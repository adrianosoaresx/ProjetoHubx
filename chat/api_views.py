from __future__ import annotations

import mimetypes
from datetime import timedelta
from io import BytesIO

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import connection, models
from django.db.models.functions import TruncDay, TruncMonth
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from PIL import Image
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import add_reaction, remove_reaction
from .metrics import chat_attachments_total, chat_categories_total
from .models import (
    ChatAttachment,
    ChatChannel,
    ChatChannelCategory,
    ChatFavorite,
    ChatMessage,
    ChatMessageReaction,
    ChatModerationLog,
    ChatNotification,
    ChatParticipant,
    RelatorioChatExport,
    TrendingTopic,
    UserChatPreference,
)
from .permissions import (
    IsChannelAdminOrOwner,
    IsChannelParticipant,
    IsMessageSenderOrAdmin,
    IsModeratorPermission,
)
from .serializers import (
    ChatAttachmentSerializer,
    ChatChannelCategorySerializer,
    ChatChannelSerializer,
    ChatMessageSerializer,
    ChatNotificationSerializer,
    ChatRetentionSerializer,
    ResumoChatSerializer,
    TrendingTopicSerializer,
    UserChatPreferenceSerializer,
)
from .services import criar_item_de_mensagem, sinalizar_mensagem
from .tasks import exportar_historico_chat, gerar_resumo_chat
from .throttles import FlagRateThrottle, UploadRateThrottle
from .utils import _scan_file

User = get_user_model()


class ChatChannelCategoryViewSet(viewsets.ModelViewSet):
    """Administração de categorias de canais."""

    serializer_class = ChatChannelCategorySerializer
    queryset = ChatChannelCategory.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):  # pragma: no cover - simple
        perms: list[type[permissions.BasePermission]] = [permissions.IsAuthenticated]
        if self.action in {"create", "partial_update", "destroy"}:
            perms.append(permissions.IsAdminUser)
        return [p() for p in perms]

    def get_queryset(self):  # pragma: no cover - simple filtering
        qs = super().get_queryset()
        nome = self.request.query_params.get("nome")
        if nome:
            qs = qs.filter(nome__icontains=nome)
        return qs.order_by("nome")

    def create(self, request: Request, *args, **kwargs) -> Response:  # pragma: no cover - simple
        resp = super().create(request, *args, **kwargs)
        if resp.status_code == status.HTTP_201_CREATED:
            chat_categories_total.inc()
        return resp


class UploadArquivoAPIView(APIView):
    """Recebe upload de arquivo e retorna URL pública."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UploadRateThrottle]

    def post(self, request: Request, *args, **kwargs) -> Response:
        arquivo = request.FILES.get("file")
        if not arquivo:
            return Response({"erro": "Arquivo obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        content_type = arquivo.content_type or mimetypes.guess_type(arquivo.name)[0] or ""
        if arquivo.size > settings.CHAT_UPLOAD_MAX_SIZE:
            return Response(
                {"erro": "Arquivo excede o tamanho máximo permitido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not any(
            content_type == mt or (mt.endswith("/") and content_type.startswith(mt))
            for mt in settings.CHAT_ALLOWED_MIME_TYPES
        ):
            return Response(
                {"erro": "Tipo de arquivo não permitido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        attachment = ChatAttachment(
            usuario=request.user,
            mime_type=content_type,
            tamanho=arquivo.size,
        )
        attachment.arquivo.save(arquivo.name, arquivo)
        url = default_storage.url(attachment.arquivo.name)

        thumb_url = ""
        if content_type.startswith("image"):
            try:
                attachment.arquivo.open()
                img = Image.open(attachment.arquivo)
                img.thumbnail((256, 256))
                thumb_io = BytesIO()
                img.save(thumb_io, format=img.format or "PNG")
                thumb_path = f"chat/thumbs/{attachment.arquivo.name.rsplit('/', 1)[-1]}"
                default_storage.save(thumb_path, ContentFile(thumb_io.getvalue()))
                thumb_url = default_storage.url(thumb_path)
                attachment.thumb_url = thumb_url
            except Exception:  # pragma: no cover - fallback se Pillow falhar
                thumb_url = ""

        infected = _scan_file(attachment.arquivo.path)
        attachment.infected = infected
        if content_type.startswith("image") and not infected:
            attachment.preview_ready = True
        attachment.save()
        chat_attachments_total.inc()

        # Remove orphan attachments older than 1 hour
        ChatAttachment.objects.filter(
            mensagem__isnull=True,
            created_at__lt=timezone.now() - timedelta(hours=1),
        ).delete()

        tipo = "file"
        if content_type.startswith("image"):
            tipo = "image"
        elif content_type.startswith("video"):
            tipo = "video"
        return Response(
            {
                "attachment_id": str(attachment.id),
                "tipo": tipo,
                "url": url if not infected else "",
                "mime_type": content_type,
                "tamanho": attachment.tamanho,
                "thumb_url": thumb_url if not infected else "",
                "infected": infected,
            }
        )


class ChavePublicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, pk: int, *args, **kwargs) -> Response:
        user = get_object_or_404(User, pk=pk)
        return Response({"chave_publica": user.chave_publica or ""})


class AtualizarChavePublicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request, *args, **kwargs) -> Response:
        chave = request.data.get("chave_publica")
        if not chave:
            return Response({"erro": "chave_publica obrigatória"}, status=status.HTTP_400_BAD_REQUEST)
        request.user.chave_publica = chave
        request.user.save(update_fields=["chave_publica"])
        return Response({"chave_publica": chave})


class UserChatPreferenceView(APIView):
    """Retorna e atualiza preferências do usuário autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request: Request) -> UserChatPreference:
        prefs, _ = UserChatPreference.all_objects.get_or_create(user=request.user)
        if prefs.deleted:
            prefs.undelete()
        return prefs

    def get(self, request: Request, *args, **kwargs) -> Response:
        prefs = self.get_object(request)
        serializer = UserChatPreferenceSerializer(prefs)
        return Response(serializer.data)

    def patch(self, request: Request, *args, **kwargs) -> Response:
        prefs = self.get_object(request)
        serializer = UserChatPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def post(self, request: Request, *args, **kwargs) -> Response:
        return self.patch(request, *args, **kwargs)


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
            categoria = self.request.query_params.get("categoria")
            if categoria:
                qs = qs.filter(categoria_id=categoria)
        return qs.select_related("categoria").prefetch_related("participants__user").distinct()

    def get_permissions(self):
        perms: list[type[permissions.BasePermission]] = [permissions.IsAuthenticated]
        if self.action in {"retrieve"}:
            perms.append(IsChannelParticipant)
        if self.action in {
            "update",
            "partial_update",
            "add_participant",
            "remove_participant",
            "export",
            "config_retencao",
        }:
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
        data = {k: v for k, v in request.data.items() if k in {"titulo", "descricao", "imagem", "categoria"}}
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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsChannelParticipant])
    def leave(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        try:
            participant = ChatParticipant.objects.get(channel=channel, user=request.user)
        except ChatParticipant.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if (participant.is_admin or participant.is_owner) and not ChatParticipant.objects.filter(
            channel=channel, is_admin=True
        ).exclude(user=request.user).exists():
            return Response({"erro": "Último administrador não pode sair"}, status=status.HTTP_400_BAD_REQUEST)
        participant.delete()
        return Response({"status": "ok"})

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated, IsChannelParticipant])
    def attachments(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        qs = ChatAttachment.objects.filter(mensagem__channel=channel)
        if not ChatParticipant.objects.filter(channel=channel, user=request.user, is_admin=True).exists():
            qs = qs.filter(infected=False)
        serializer = ChatAttachmentSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["patch"],
        url_path="config-retention",
        permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner],
    )
    def config_retencao(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        serializer = ChatRetentionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel.retencao_dias = serializer.validated_data["retencao_dias"]
        channel.save(update_fields=["retencao_dias"])
        return Response({"retencao_dias": channel.retencao_dias})

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
        permission_classes=[permissions.IsAuthenticated, IsChannelParticipant],
    )
    def resumos(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        periodo = request.query_params.get("periodo")
        qs = channel.resumos.all()
        if periodo in {"diario", "semanal"}:
            qs = qs.filter(periodo=periodo)
        serializer = ResumoChatSerializer(qs, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"resumos/(?P<resumo_id>[0-9a-f-]+)",
        permission_classes=[permissions.IsAuthenticated, IsChannelParticipant],
    )
    def resumo_detail(self, request: Request, pk: str | None = None, resumo_id: str | None = None) -> Response:
        channel = self.get_object()
        resumo = get_object_or_404(channel.resumos, pk=resumo_id)
        serializer = ResumoChatSerializer(resumo)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsChannelParticipant],
        url_path="gerar-resumo",
    )
    def gerar_resumo(self, request: Request, pk: str | None = None) -> Response:
        channel = self.get_object()
        periodo = request.data.get("periodo") or request.query_params.get("periodo")
        if periodo not in {"diario", "semanal"}:
            return Response({"erro": "periodo inválido"}, status=status.HTTP_400_BAD_REQUEST)
        gerar_resumo_chat.delay(str(channel.id), periodo)
        return Response({"status": "agendado"})

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
        qs = channel.messages.select_related("remetente").order_by("-created_at")
        if before:
            dt = parse_datetime(before)
            if dt:
                qs = qs.filter(created_at__lt=dt)
            else:
                try:
                    ref_msg = channel.messages.get(pk=before)
                    qs = qs.filter(created_at__lt=ref_msg.created_at)
                except ChatMessage.DoesNotExist:
                    pass
        if inicio and not before:
            dt = parse_datetime(inicio)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        if fim and not before:
            dt = parse_datetime(fim)
            if dt:
                qs = qs.filter(created_at__lte=dt)
        limit = ChatMessagePagination.page_size + 1
        items = list(qs[:limit])
        has_more = len(items) == limit
        if has_more:
            items = items[:-1]
        serializer = ChatMessageSerializer(items, many=True, context={"request": request})
        data = []
        for obj, item in zip(items, serializer.data):
            user_emojis = list(
                ChatMessageReaction.objects.filter(message=obj, user=request.user).values_list("emoji", flat=True)
            )
            item["user_reactions"] = user_emojis
            data.append(item)
        return Response({"messages": data, "has_more": has_more})


class ChatAttachmentViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = ChatAttachment.objects.select_related("mensagem__channel")
    serializer_class = ChatAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        attachment = self.get_object()
        channel = attachment.mensagem.channel if attachment.mensagem else None
        if not channel or not IsChannelAdminOrOwner().has_object_permission(request, self, channel):
            return Response(status=status.HTTP_403_FORBIDDEN)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def get_serializer_context(self):  # type: ignore[override]
        context = super().get_serializer_context()
        context["channel_pk"] = self.kwargs.get("channel_pk")
        return context

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
            .select_related("remetente", "reply_to", "reply_to__remetente")
            .prefetch_related("lido_por")
            .order_by("created_at")
        )

    def perform_create(self, serializer: ChatMessageSerializer) -> None:
        channel = get_object_or_404(ChatChannel, pk=self.kwargs["channel_pk"])
        attachment_id = serializer.validated_data.get("attachment_id")
        if attachment_id and not ChatAttachment.objects.filter(
            id=attachment_id, usuario=self.request.user, mensagem__isnull=True
        ).exists():
            raise ValidationError({"attachment_id": "Anexo inválido"})
        if channel.e2ee_habilitado:
            data = serializer.validated_data
            if data.get("conteudo"):
                raise ValidationError({"conteudo": "Proibido quando E2EE habilitado"})
            missing = [k for k in ("conteudo_cifrado", "alg", "key_version") if not data.get(k)]
            if missing:
                raise ValidationError({m: "Obrigatório quando E2EE habilitado" for m in missing})
        serializer.save(channel=channel)

    def list(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        queryset = self.get_queryset()
        desde = request.query_params.get("desde")
        ate = request.query_params.get("ate")
        if desde:
            dt = parse_datetime(desde)
            if dt:
                queryset = queryset.filter(created_at__gte=dt)
        if ate:
            dt = parse_datetime(ate)
            if dt:
                queryset = queryset.filter(created_at__lte=dt)
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
                queryset = queryset.annotate(search=SearchVector("conteudo", config="portuguese")).filter(
                    search=SearchQuery(termo)
                )
            else:
                queryset = queryset.filter(conteudo__icontains=termo)

        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if desde:
            dt = parse_datetime(desde)
            if dt:
                queryset = queryset.filter(created_at__gte=dt)
        if ate:
            dt = parse_datetime(ate)
            if dt:
                queryset = queryset.filter(created_at__lte=dt)
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
        permission_classes=[permissions.IsAuthenticated, IsChannelParticipant],
    )
    def criar_item(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        inicio = parse_datetime(request.data.get("inicio")) if request.data.get("inicio") else None
        fim = parse_datetime(request.data.get("fim")) if request.data.get("fim") else None
        try:
            item = criar_item_de_mensagem(
                mensagem=msg,
                usuario=request.user,
                tipo=request.data.get("tipo", ""),
                titulo=request.data.get("titulo", ""),
                descricao=request.data.get("descricao"),
                inicio=inicio,
                fim=fim,
            )
        except PermissionError:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except (ValueError, NotImplementedError) as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        link = ""
        if request.data.get("tipo") == "evento":
            link = reverse("agenda:evento_detalhe", args=[item.pk])
        elif request.data.get("tipo") == "tarefa":
            link = reverse("agenda:tarefa_detalhe", args=[item.pk])
        return Response(
            {"id": str(item.pk), "titulo": item.titulo, "link": link},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post", "delete"])
    def favorite(self, request: Request, channel_pk: str, pk: str) -> Response:
        """Adiciona ou remove uma mensagem dos favoritos do usuário."""
        msg = self.get_object()
        if request.method.lower() == "post":
            if ChatFavorite.objects.filter(user=request.user).count() >= 1000:
                return Response(status=status.HTTP_409_CONFLICT)
            ChatFavorite.objects.get_or_create(user=request.user, message=msg)
            return Response(status=status.HTTP_201_CREATED)
        ChatFavorite.objects.filter(user=request.user, message=msg).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def mark_read(self, request: Request, channel_pk: str, pk: str) -> Response:
        """Marca a mensagem como lida pelo usuário autenticado."""
        msg = self.get_object()
        msg.lido_por.add(request.user)
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
        exists = ChatMessageReaction.objects.filter(message=msg, user=request.user, emoji=emoji).exists()
        if exists:
            remove_reaction(msg, request.user, emoji)
        else:
            add_reaction(msg, request.user, emoji)
        user_emojis = list(
            ChatMessageReaction.objects.filter(message=msg, user=request.user).values_list("emoji", flat=True)
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
                    "created_at": msg.created_at.isoformat(),
                    "reactions": counts,
                    "actor": request.user.username,
                    "user_reactions": user_emojis,
                    "reply_to": str(msg.reply_to_id) if msg.reply_to_id else None,
                },
            )
        data = self.get_serializer(msg).data
        data["reactions"] = counts
        data["user_reactions"] = user_emojis
        return Response(data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsChannelAdminOrOwner],
    )
    def restore(self, request: Request, channel_pk: str, pk: str) -> Response:
        """Restore message content from a moderation log entry."""
        msg = self.get_object()
        log_id = request.data.get("log_id")
        if not log_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        log = get_object_or_404(ChatModerationLog, pk=log_id, message=msg)
        msg.restore_from_log(log, request.user)
        return Response(self.get_serializer(msg).data)

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
            .order_by("-created_at")
        )

    @action(detail=True, methods=["post"])
    def ler(self, request: Request, pk: str | None = None) -> Response:
        notif = self.get_object()
        notif.lido = True
        notif.save(update_fields=["lido"])
        return Response(self.get_serializer(notif).data)


class ChatFavoriteViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista mensagens favoritas do usuário."""

    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ChatMessagePagination

    def get_queryset(self):
        return (
            ChatFavorite.objects.filter(user=self.request.user)
            .select_related("message", "message__channel", "message__remetente")
            .order_by("-created_at")
        )

    def list(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        items = page if page is not None else queryset
        messages = [fav.message for fav in items]
        serializer = self.get_serializer(messages, many=True)
        grouped: dict[str, list[dict[str, object]]] = {}
        for fav, data in zip(items, serializer.data):
            channel_id = str(fav.message.channel_id)
            grouped.setdefault(channel_id, []).append(data)
        if page is not None:
            return self.get_paginated_response(grouped)
        return Response(grouped)


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
                "created_at": m.created_at.isoformat(),
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
        msg.save(update_fields=["hidden_at", "updated_at"])
        ChatModerationLog.objects.create(message=msg, action="approve", moderator=request.user)
        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def remove(self, request: Request, pk: str | None = None) -> Response:
        msg = get_object_or_404(ChatMessage, pk=pk)
        ChatModerationLog.objects.create(message=msg, action="remove", moderator=request.user)
        msg.notificacoes.all().delete()
        msg.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMetricsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request: Request) -> Response:
        inicio = request.query_params.get("inicio")
        fim = request.query_params.get("fim")
        categoria = request.query_params.get("categoria")
        canal = request.query_params.get("canal")
        periodo = request.query_params.get("periodo", "dia")
        trunc = TruncDay if periodo == "dia" else TruncMonth

        msgs = ChatMessage.objects.all()
        if canal:
            msgs = msgs.filter(channel_id=canal)
        if categoria:
            msgs = msgs.filter(channel__categoria_id=categoria)
        if inicio:
            dt = parse_datetime(inicio)
            if dt:
                msgs = msgs.filter(created_at__gte=dt)
        if fim:
            dt = parse_datetime(fim)
            if dt:
                msgs = msgs.filter(created_at__lte=dt)

        msg_agg = (
            msgs.annotate(p=trunc("created_at"))
            .values("p")
            .annotate(
                total_mensagens=models.Count("id"),
                mensagens_text=models.Count("id", filter=models.Q(tipo="text")),
                mensagens_image=models.Count("id", filter=models.Q(tipo="image")),
                mensagens_video=models.Count("id", filter=models.Q(tipo="video")),
                mensagens_file=models.Count("id", filter=models.Q(tipo="file")),
                total_reacoes=models.Count("reaction_details"),
                mensagens_sinalizadas=models.Count("flags"),
                mensagens_ocultadas=models.Count("id", filter=models.Q(hidden_at__isnull=False)),
            )
        )

        att_qs = ChatAttachment.objects.filter(mensagem__in=msgs)
        att_agg = (
            att_qs.annotate(p=trunc("created_at"))
            .values("p")
            .annotate(
                total_anexos=models.Count("id"),
                tamanho_total_anexos=models.Sum("tamanho"),
            )
        )

        data: dict[str, dict[str, int]] = {}
        for item in msg_agg:
            key = item["p"].date() if periodo == "dia" else item["p"].strftime("%Y-%m")
            data[key] = {
                "total_mensagens": item["total_mensagens"],
                "mensagens_text": item["mensagens_text"],
                "mensagens_image": item["mensagens_image"],
                "mensagens_video": item["mensagens_video"],
                "mensagens_file": item["mensagens_file"],
                "total_reacoes": item["total_reacoes"],
                "mensagens_sinalizadas": item["mensagens_sinalizadas"],
                "mensagens_ocultadas": item["mensagens_ocultadas"],
            }
        for item in att_agg:
            key = item["p"].date() if periodo == "dia" else item["p"].strftime("%Y-%m")
            data.setdefault(key, {})["total_anexos"] = item["total_anexos"]
            data.setdefault(key, {})["tamanho_total_anexos"] = item["tamanho_total_anexos"] or 0

        results = []
        for key in sorted(data):
            val = data[key]
            results.append(
                {
                    "periodo": str(key),
                    "total_mensagens": val.get("total_mensagens", 0),
                    "mensagens_por_tipo": {
                        "text": val.get("mensagens_text", 0),
                        "image": val.get("mensagens_image", 0),
                        "video": val.get("mensagens_video", 0),
                        "file": val.get("mensagens_file", 0),
                    },
                    "total_reacoes": val.get("total_reacoes", 0),
                    "mensagens_sinalizadas": val.get("mensagens_sinalizadas", 0),
                    "mensagens_ocultadas": val.get("mensagens_ocultadas", 0),
                    "total_anexos": val.get("total_anexos", 0),
                    "tamanho_total_anexos": val.get("tamanho_total_anexos", 0),
                }
            )
        return Response({"resultados": results})


class TrendingTopicsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        canal_id = request.query_params.get("canal")
        dias = int(request.query_params.get("dias", 7))
        qs = TrendingTopic.objects.all()
        if canal_id:
            qs = qs.filter(canal_id=canal_id)
        inicio = timezone.now() - timedelta(days=dias)
        qs = qs.filter(periodo_fim__gte=inicio).order_by("-frequencia")[:10]
        serializer = TrendingTopicSerializer(qs, many=True)
        return Response(serializer.data)
