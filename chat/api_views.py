from __future__ import annotations

import json
from io import StringIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from .api import add_reaction
from .models import ChatConversation, ChatMessage, ChatMessageFlag, RelatorioChatExport
from .serializers import ChatMessageSerializer


class ChatMessageViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin, mixins.RetrieveModelMixin):
    queryset = ChatMessage.objects.select_related("sender", "conversation")
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def pin(self, request: Request, pk: str) -> Response:
        msg = self.get_object()
        msg.pinned_at = timezone.now()
        msg.save(update_fields=["pinned_at"])
        serializer = self.get_serializer(msg)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def react(self, request: Request, pk: str) -> Response:
        msg = self.get_object()
        emoji = request.data.get("emoji")
        if emoji:
            add_reaction(msg, emoji)
        serializer = self.get_serializer(msg)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def flag(self, request: Request, pk: str) -> Response:
        msg = self.get_object()
        ChatMessageFlag.objects.get_or_create(message=msg, user=request.user)
        serializer = self.get_serializer(msg)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def revisar(self, request: Request, pk: str) -> Response:
        msg = self.get_object()
        acao = request.data.get("acao")
        if acao == "aprovar":
            msg.hidden_at = None
            msg.flags.all().delete()
            msg.save(update_fields=["hidden_at", "updated_at"])
        elif acao == "remover":
            msg.delete()
            return Response(status=204)
        serializer = self.get_serializer(msg)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def exportar_canal(request: Request, pk: str) -> Response:
    formato = request.GET.get("formato", "json")
    canal = get_object_or_404(ChatConversation, pk=pk)
    mensagens = canal.messages.select_related("sender").order_by("created_at")
    data = [
        {
            "remetente": m.sender_id,
            "conteudo": m.conteudo,
            "tipo": m.tipo,
            "timestamp": m.created_at.isoformat(),
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
    else:
        json.dump(data, buffer)
        ext = "json"
    path = default_storage.save(f"chat/exports/{canal.pk}.{ext}", ContentFile(buffer.getvalue().encode()))
    rel = RelatorioChatExport.objects.create(
        channel=canal,
        formato=ext,
        gerado_por=request.user,
        arquivo_url=default_storage.url(path),
    )
    return Response({"url": rel.arquivo_url})
