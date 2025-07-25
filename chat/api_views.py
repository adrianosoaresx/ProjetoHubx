from __future__ import annotations

from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .api import add_reaction
from .models import ChatMessage
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
