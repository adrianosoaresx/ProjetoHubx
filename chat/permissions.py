"""Permissões customizadas para canais e mensagens de chat."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from .models import ChatChannel, ChatMessage, ChatParticipant

User = get_user_model()


class IsChannelParticipant(BasePermission):
    """Permite acesso apenas a participantes do canal."""

    message = "Usuário não participa deste canal."

    def _get_channel(self, view, obj: Any | None) -> ChatChannel | None:  # pragma: no cover - helper
        if isinstance(obj, ChatChannel):
            return obj
        if isinstance(obj, ChatMessage):
            return obj.channel
        channel_id = view.kwargs.get("channel_pk") or view.kwargs.get("pk")
        if channel_id:
            try:
                return ChatChannel.objects.get(pk=channel_id)
            except ChatChannel.DoesNotExist:
                return None
        return None

    def has_permission(self, request, view) -> bool:
        channel = self._get_channel(view, None)
        if channel is None:
            return True  # objeto será verificado posteriormente
        return ChatParticipant.objects.filter(channel=channel, user=request.user).exists()

    def has_object_permission(self, request, view, obj) -> bool:
        channel = self._get_channel(view, obj)
        if channel is None:
            return False
        return ChatParticipant.objects.filter(channel=channel, user=request.user).exists()


class IsChannelAdminOrOwner(BasePermission):
    """Apenas administradores ou proprietários do canal."""

    message = "Permissão negada."  # pragma: no cover - simple message

    def has_object_permission(self, request, view, obj) -> bool:
        if isinstance(obj, ChatMessage):
            channel = obj.channel
        else:
            channel = obj
        try:
            participant = ChatParticipant.objects.get(channel=channel, user=request.user)
        except ChatParticipant.DoesNotExist:
            return False
        return participant.is_admin or participant.is_owner

    def has_permission(self, request, view) -> bool:  # pragma: no cover - object handled
        channel_id = view.kwargs.get("channel_pk") or view.kwargs.get("pk")
        if not channel_id:
            return True
        try:
            participant = ChatParticipant.objects.get(channel_id=channel_id, user=request.user)
        except ChatParticipant.DoesNotExist:
            return False
        return participant.is_admin or participant.is_owner


class IsMessageSenderOrAdmin(BasePermission):
    """Permite alteração apenas ao remetente ou admin do canal."""

    message = "Apenas o remetente ou administradores podem alterar a mensagem."

    def has_object_permission(self, request, view, obj: ChatMessage) -> bool:
        if obj.remetente_id == request.user.id:
            return True
        try:
            participant = ChatParticipant.objects.get(channel=obj.channel, user=request.user)
        except ChatParticipant.DoesNotExist:  # pragma: no cover - defensive
            return False
        return participant.is_admin or participant.is_owner
