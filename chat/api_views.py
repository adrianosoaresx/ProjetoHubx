from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import connection, models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
import mimetypes
from django.contrib.postgres.search import SearchQuery, SearchVector

from core.permissions import IsModeratorUser

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .api import add_reaction, remove_reaction
from .models import (
    ChatChannel,
    ChatMessage,
    ChatModerationLog,
    ChatMessageReaction,
    ChatNotification,
    ChatParticipant,
    RelatorioChatExport,
)
from .permissions import (
    IsChannelAdminOrOwner,
    IsChannelParticipant,
    IsMessageSenderOrAdmin,
    IsModeratorPermission,
)
from .serializers import (
    ChatChannelSerializer,
    ChatMessageSerializer,
    ChatNotificationSerializer,
)
from .services import sinalizar_mensagem
from .tasks import exportar_historico_chat
from .throttles import UploadRateThrottle, FlagRateThrottle

User = get_user_model()


class UploadArquivoAPIView(APIView):
    """Recebe upload de arquivo e retorna URL pública."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UploadRateThrottle]


    def post(self, request: Request, *args, **kwargs) -> Response:
        arquivo = request.FILES.get("file")
        if not arquivo:
            return Response({"erro": "Arquivo obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        path = default_storage.save(f"chat/uploads/{arquivo.name}", arquivo)
        url = default_storage.url(path)
        content_type = arquivo.content_type or mimetypes.guess_type(arquivo.name)[0] or ""
        tipo = "file"
        if content_type.startswith("image"):
            tipo = "image"
        elif content_type.startswith("video"):
            tipo = "video"
        return Response({"tipo": tipo, "url": url})


class ChatChannelViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de canais de chat.

    Lista somente canais do usuário autenticado e permite
    ações administrativas como adicionar participantes ou
    exportar o histórico de mensagens.
    """

    serializer_class = ChatChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ChatChannel.objects.all()

    def get_queryset(self):
        user = self.request.user
        qs = ChatChannel.objects.all()
        if self.action == "list":
            qs = qs.filter(participants__user=user)
        return qs.select_related().prefetch_related("participants__user").distinct()

    def get_permissions(self):
        perms: list[type[permissions.BasePermission]] = [permissions.IsAuthenticated]
        if self.action in {"retrieve"}:
            perms.append(IsChannelParticipant)
        if self.action in {"update", "partial_update", "add_participant", "remove_participant", "export"}:
            perms.append(IsChannelAdminOrOwner)
        return [p() for p in perms]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contexto_tipo = serializer.validated_data.get("contexto_tipo")
        if contexto_tipo != "privado" and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        canal = serializer.save()
        out_serializer = self.get_serializer(canal)
        headers = self.get_success_headers(out_serializer.data)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        kwargs.setdefault("partial", False)
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        instance = self.get_object()
        data = {k: v for k, v in request.data.items() if k in {"titulo", "descricao", "imagem"}}
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        return Response(status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner])
    def add_participant(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        user_ids = request.data.get("usuarios") or []
        if isinstance(user_ids, str):
            user_ids = [user_ids]
        users = User.objects.filter(id__in=user_ids)
        for u in users:
            ChatParticipant.objects.get_or_create(channel=channel, user=u)
        return Response({"adicionados": [u.id for u in users]})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner])
    def remove_participant(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        user_ids = request.data.get("usuarios") or []
        if isinstance(user_ids, str):
            user_ids = [user_ids]
        ChatParticipant.objects.filter(channel=channel, user__id__in=user_ids).delete()
        return Response({"removidos": user_ids})

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner],
    )
    def export(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        formato = request.query_params.get("formato", "json")
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        tipos_list = request.query_params.getlist("tipos")
        if not tipos_list:
            tipos = request.query_params.get("tipos")
            tipos_list = tipos.split(",") if tipos else None
        rel = RelatorioChatExport.objects.create(
            channel=channel,
            formato=formato,
            gerado_por=request.user,
            status="gerando",
        )
        exportar_historico_chat.delay(
            channel.id,
            formato,
            inicio,
            fim,
            tipos_list,
            rel.id,
        )
        return Response({"relatorio_id": str(rel.id)}, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=True,
        methods=["get"],
        url_path="messages/history",
        permission_classes=[permissions.IsAuthenticated, IsChannelParticipant],
    )
    def messages_history(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        before = request.query_params.get("before")
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        qs = channel.messages.select_related("remetente").order_by("-created")
        if before:
            try:
                ref_msg = channel.messages.get(pk=before)
                qs = qs.filter(created__lt=ref_msg.created)
            except ChatMessage.DoesNotExist:
                pass
        else:
            if inicio:
                dt = parse_datetime(inicio)
                if dt:
                    qs = qs.filter(created__gte=dt)
            if fim:
                dt = parse_datetime(fim)
                if dt:
                    qs = qs.filter(created__lte=dt)
        limit = ChatMessagePagination.page_size + 1
        items = list(qs[:limit])
        has_more = len(items) == limit
        if has_more:
            items = items[:-1]
        items.reverse()
        serializer = ChatMessageSerializer(items, many=True, context={"request": request})
        data = []
        for obj, item in zip(items, serializer.data):
            user_emojis = list(
                ChatMessageReaction.objects.filter(message=obj, user=request.user).values_list(
                    "emoji", flat=True
                )
            )
            item["user_reactions"] = user_emojis
            data.append(item)
        return Response({"messages": data, "has_more": has_more})


class ChatMessagePagination(PageNumberPagination):
    page_size = 20


class ChatMessageViewSet(viewsets.ModelViewSet):
    """Gerencia mensagens de um canal.

    Oferece listagem paginada, criação de mensagens e
    ações customizadas como reagir ou sinalizar conteúdo.
    """

    serializer_class = ChatMessageSerializer
    permission_classes: list[type[permissions.BasePermission]] = [
        permissions.IsAuthenticated,
        IsChannelParticipant,
    ]
    pagination_class = ChatMessagePagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    lookup_field = "id"
    lookup_url_kwarg = "pk"

    def get_permissions(self):
        perms: list[type[permissions.BasePermission]] = [
            permissions.IsAuthenticated,
            IsChannelParticipant,
        ]
        if self.action in {"partial_update", "destroy"}:
            perms.append(IsMessageSenderOrAdmin)
        return [p() for p in perms]

    def get_queryset(self):
        channel_id = self.kwargs["channel_pk"]
        return (
            ChatMessage.objects.filter(channel_id=channel_id)
            .select_related("remetente")
            .prefetch_related("lido_por")
            .order_by("created")
        )

    def perform_create(self, serializer: ChatMessageSerializer) -> None:
        channel = get_object_or_404(ChatChannel, pk=self.kwargs["channel_pk"])
        serializer.save(channel=channel)

    def list(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        queryset = self.get_queryset()
        desde = request.query_params.get("desde")
        ate = request.query_params.get("ate")
        if desde:
            dt = parse_datetime(desde)
            if dt:
                queryset = queryset.filter(created__gte=dt)
        if ate:
            dt = parse_datetime(ate)
            if dt:
                queryset = queryset.filter(created__lte=dt)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request: Request, channel_pk: str) -> Response:
        """Busca mensagens por palavra-chave e filtros."""
        queryset = self.get_queryset()
        termo = request.query_params.get("q")
        tipo = request.query_params.get("tipo")
        desde = request.query_params.get("desde")
        ate = request.query_params.get("ate")

        if termo:
            if connection.vendor == "postgresql":
                queryset = queryset.annotate(
                    search=SearchVector("conteudo", config="portuguese")
                ).filter(search=SearchQuery(termo))
            else:
                queryset = queryset.filter(conteudo__icontains=termo)

        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if desde:
            dt = parse_datetime(desde)
            if dt:
                queryset = queryset.filter(created__gte=dt)
        if ate:
            dt = parse_datetime(ate)
            if dt:
                queryset = queryset.filter(created__lte=dt)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        msg = self.get_object()
        data = {k: v for k, v in request.data.items() if k in {"conteudo"}}
        serializer = self.get_serializer(msg, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous = msg.conteudo
        self.perform_update(serializer)
        ChatModerationLog.objects.create(
            message=msg,
            action="edit",
            moderator=request.user,
            previous_content=previous,
        )
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        msg = self.get_object()
        ChatModerationLog.objects.create(
            message=msg,
            action="remove",
            moderator=request.user,
            previous_content=msg.conteudo,
        )
        msg.notificacoes.all().delete()
        msg.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner],
    )
    def pin(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        msg.pinned_at = timezone.now()
        msg.save(update_fields=["pinned_at"])
        return Response(self.get_serializer(msg).data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner],
    )
    def unpin(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        msg.pinned_at = None
        msg.save(update_fields=["pinned_at"])
        return Response(self.get_serializer(msg).data)

    @action(detail=True, methods=["post"])
    def react(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        emoji = request.data.get("emoji")
        if not emoji:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        exists = ChatMessageReaction.objects.filter(
            message=msg, user=request.user, emoji=emoji
        ).exists()
        if exists:
            remove_reaction(msg, request.user, emoji)
        else:
            add_reaction(msg, request.user, emoji)
        user_emojis = list(
            ChatMessageReaction.objects.filter(message=msg, user=request.user).values_list(
                "emoji", flat=True
            )
        )
        counts = msg.reaction_counts()
        layer = get_channel_layer()
        if layer:
            async_to_sync(layer.group_send)(
                f"chat_{msg.channel_id}",
                {
                    "type": "chat.message",
                    "id": str(msg.id),
                    "remetente": msg.remetente.username,
                    "tipo": msg.tipo,
                    "conteudo": msg.conteudo,
                    "arquivo_url": msg.arquivo.url if msg.arquivo else None,
                    "created": msg.created.isoformat(),
                    "reactions": counts,
                    "actor": request.user.username,
                    "user_reactions": user_emojis,
                },
            )
        data = self.get_serializer(msg).data
        data["reactions"] = counts
        data["user_reactions"] = user_emojis
        return Response(data)

    @action(detail=True, methods=["post"], throttle_classes=[FlagRateThrottle])
    def flag(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        try:
            total = sinalizar_mensagem(msg, request.user)
        except ValueError:
            return Response(status=status.HTTP_409_CONFLICT)
        return Response({"flags": total})


class ChatNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem e leitura de notificações de chat."""

    serializer_class = ChatNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ChatNotification.objects.filter(usuario=self.request.user)
            .select_related("mensagem", "mensagem__channel", "usuario")
            .order_by("-created")
        )

    @action(detail=True, methods=["post"])
    def ler(self, request: Request, pk: str | None = None) -> Response:
        notif = self.get_object()
        notif.lido = True
        notif.save(update_fields=["lido"])
        return Response(self.get_serializer(notif).data)


class ModeracaoViewSet(viewsets.ViewSet):
    """Endpoints para moderação de mensagens sinalizadas."""

    permission_classes = [permissions.IsAuthenticated, IsModeratorPermission]

    def list(self, request: Request) -> Response:
        msgs = (
            ChatMessage.objects.filter(flags__isnull=False)
            .annotate(flags_count=models.Count("flags"))
            .select_related("remetente", "channel")
        )
        data = [
            {
                "id": str(m.id),
                "conteudo": m.conteudo,
                "remetente": m.remetente.username,
                "canal": str(m.channel_id),
                "created": m.created.isoformat(),
                "flags": m.flags_count,
                "hidden": bool(m.hidden_at),
            }
            for m in msgs
        ]
        return Response(data)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        msg = get_object_or_404(ChatMessage, pk=pk)
        msg.hidden_at = None
        msg.flags.all().delete()
        msg.save(update_fields=["hidden_at", "modified"])
        ChatModerationLog.objects.create(message=msg, action="approve", moderator=request.user)
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def remove(self, request: Request, pk: str | None = None) -> Response:
        msg = get_object_or_404(ChatMessage, pk=pk)
        ChatModerationLog.objects.create(message=msg, action="remove", moderator=request.user)
        msg.notificacoes.all().delete()
        msg.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
