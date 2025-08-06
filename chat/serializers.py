from __future__ import annotations

from typing import Any, Iterable

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ChatChannel, ChatMessage, ChatNotification
from .services import criar_canal, enviar_mensagem

User = get_user_model()


class ChatChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatChannel
        fields = [
            "id",
            "contexto_tipo",
            "contexto_id",
            "titulo",
            "descricao",
            "imagem",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]

    def create(self, validated_data: dict[str, Any]) -> ChatChannel:
        request = self.context["request"]
        participantes_ids = self.initial_data.get("participantes") or []
        if isinstance(participantes_ids, str):  # pragma: no cover - defensive
            participantes_ids = [participantes_ids]
        participantes: Iterable[User] = User.objects.filter(id__in=participantes_ids)
        return criar_canal(
            criador=request.user,
            contexto_tipo=validated_data.get("contexto_tipo"),
            contexto_id=validated_data.get("contexto_id"),
            titulo=validated_data.get("titulo"),
            descricao=validated_data.get("descricao"),
            participantes=participantes,
        )

    def to_representation(self, instance: ChatChannel) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["participantes"] = instance.participants.count()
        last_msg = instance.messages.select_related("remetente").order_by("-created").first()
        if last_msg:
            data["ultima_mensagem"] = ChatMessageSerializer(last_msg, context=self.context).data
        return data


class ChatMessageSerializer(serializers.ModelSerializer):
    remetente = serializers.PrimaryKeyRelatedField(read_only=True)
    reactions = serializers.SerializerMethodField()
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=ChatMessage.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "channel",
            "remetente",
            "tipo",
            "conteudo",
            "arquivo",
            "reply_to",
            "reactions",
            "pinned_at",
            "hidden_at",
            "created",
        ]
        read_only_fields = [
            "id",
            "remetente",
            "created",
            "pinned_at",
            "hidden_at",
            "channel",
        ]

    def create(self, validated_data: dict[str, Any]) -> ChatMessage:
        channel = validated_data["channel"]
        remetente = self.context["request"].user
        tipo = validated_data.get("tipo", "text")
        conteudo = validated_data.get("conteudo", "")
        arquivo = validated_data.get("arquivo")
        reply_to = validated_data.get("reply_to")
        return enviar_mensagem(
            canal=channel,
            remetente=remetente,
            tipo=tipo,
            conteudo=conteudo,
            arquivo=arquivo,
            reply_to=reply_to,
        )

    def to_representation(self, instance: ChatMessage) -> dict[str, Any]:
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.arquivo:
            url = instance.arquivo.url
            if request:
                url = request.build_absolute_uri(url)
            data["arquivo_url"] = url
        return data

    def get_reactions(self, obj: ChatMessage) -> dict[str, int]:
        return obj.reaction_counts()


class ChatNotificationSerializer(serializers.ModelSerializer):
    mensagem_conteudo = serializers.SerializerMethodField()
    canal_url = serializers.SerializerMethodField()
    canal_titulo = serializers.CharField(source="mensagem.channel.titulo", read_only=True)
    mensagem_tipo = serializers.CharField(source="mensagem.tipo", read_only=True)
    canal_id = serializers.CharField(source="mensagem.channel_id", read_only=True)
    reply_to = serializers.UUIDField(
        source="mensagem.reply_to_id", read_only=True, allow_null=True
    )

    class Meta:
        model = ChatNotification
        fields = [
            "id",
            "usuario",
            "mensagem",
            "mensagem_tipo",
            "mensagem_conteudo",
            "canal_id",
            "canal_titulo",
            "canal_url",
            "reply_to",
            "lido",
            "created",
        ]
        read_only_fields = ["id", "created"]

    def get_mensagem_conteudo(self, obj: ChatNotification) -> str:
        msg = obj.mensagem
        if msg.tipo == "text":
            return msg.conteudo
        return msg.conteudo or (msg.arquivo.url if msg.arquivo else "")

    def get_canal_url(self, obj: ChatNotification) -> str:
        request = self.context.get("request")
        url = obj.mensagem.channel.get_absolute_url()
        if request:
            return request.build_absolute_uri(url)
        return url
