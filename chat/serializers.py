from __future__ import annotations

from rest_framework import serializers

from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "conversation",
            "sender",
            "tipo",
            "conteudo",
            "arquivo",
            "pinned_at",
            "reactions",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "created_at"]
