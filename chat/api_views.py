from __future__ import annotations

import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import IsModeratorUser

from .api import add_reaction
from .models import ChatChannel, ChatMessage, ChatMessageFlag, ChatModerationLog, ChatParticipant, RelatorioChatExport
from .permissions import IsChannelAdminOrOwner, IsChannelParticipant
from .serializers import ChatChannelSerializer, ChatMessageSerializer

User = get_user_model()


class ChatChannelViewSet(viewsets.ModelViewSet):
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
        if self.action in {"update", "partial_update", "add_participant", "remove_participant"}:
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


class ChatMessagePagination(PageNumberPagination):
    page_size = 20


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChannelParticipant]
    pagination_class = ChatMessagePagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        channel_id = self.kwargs["channel_pk"]
        return (
            ChatMessage.objects.filter(channel_id=channel_id)
            .select_related("remetente")
            .prefetch_related("lido_por")
            .order_by("timestamp")
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
                queryset = queryset.filter(timestamp__gte=dt)
        if ate:
            dt = parse_datetime(ate)
            if dt:
                queryset = queryset.filter(timestamp__lte=dt)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsModeratorUser])
    def pin(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        msg.pinned_at = timezone.now()
        msg.save(update_fields=["pinned_at"])
        return Response(self.get_serializer(msg).data)

    @action(detail=True, methods=["post"])
    def react(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        emoji = request.data.get("emoji")
        if emoji:
            add_reaction(msg, emoji)
        return Response(self.get_serializer(msg).data)

    @action(detail=True, methods=["post"])
    def flag(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        ChatMessageFlag.objects.get_or_create(message=msg, user=request.user)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsModeratorUser])
    def moderate(self, request: Request, channel_pk: str, pk: str) -> Response:
        msg = self.get_object()
        acao = request.data.get("acao")
        if acao == "approve":
            msg.hidden_at = None
            msg.flags.all().delete()
            msg.save(update_fields=["hidden_at", "updated_at"])
            ChatModerationLog.objects.create(message=msg, action="approve", moderator=request.user)
            return Response(self.get_serializer(msg).data)
        if acao == "remove":
            ChatModerationLog.objects.create(message=msg, action="remove", moderator=request.user)
            msg.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Ação inválida."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsModeratorUser])
def exportar_conversa(request: Request, channel_id: str) -> Response:
    formato = request.GET.get("formato", "json")
    canal = get_object_or_404(ChatChannel, pk=channel_id)
    mensagens = canal.messages.filter(hidden_at__isnull=True).select_related("remetente").order_by("timestamp")
    data = [
        {
            "remetente": m.remetente_id,
            "conteudo": m.conteudo,
            "tipo": m.tipo,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in mensagens
    ]
    buffer = StringIO()
    if formato == "csv":
        import csv

        writer = (
            csv.DictWriter(buffer, fieldnames=data[0].keys())
            if data
            else csv.DictWriter(buffer, fieldnames=["remetente", "conteudo", "tipo", "timestamp"])
        )
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        ext = "csv"
        path = default_storage.save(f"chat/exports/{canal.id}.{ext}", ContentFile(buffer.getvalue()))
    else:
        json.dump(data, buffer)
        ext = "json"
        path = default_storage.save(f"chat/exports/{canal.id}.{ext}", ContentFile(buffer.getvalue().encode()))
    rel = RelatorioChatExport.objects.create(
        channel=canal,
        formato=ext,
        gerado_por=request.user,
        arquivo_url=default_storage.url(path),
    )
    return Response({"url": rel.arquivo_url})
