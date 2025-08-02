from __future__ import annotations

from rest_framework import serializers

from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "channel",
            "remetente",
            "tipo",
            "conteudo",
            "arquivo",
            "pinned_at",
            "reactions",
            "timestamp",
        ]
        read_only_fields = ["id", "remetente", "timestamp"]
