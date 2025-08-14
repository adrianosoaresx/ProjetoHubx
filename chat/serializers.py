from __future__ import annotations

from typing import Any, Iterable

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    ChatAttachment,
    ChatChannel,
    ChatChannelCategory,
    ChatMessage,
    ChatNotification,
    ResumoChat,
    TrendingTopic,
    UserChatPreference,
)
from .services import criar_canal, enviar_mensagem

User = get_user_model()


class ChatChannelCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatChannelCategory
        fields = ["id", "nome", "descricao", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChatChannelSerializer(serializers.ModelSerializer):
    e2ee_habilitado = serializers.BooleanField(read_only=True)
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=ChatChannelCategory.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ChatChannel
        fields = [
            "id",
            "contexto_tipo",
            "contexto_id",
            "titulo",
            "descricao",
            "imagem",
            "e2ee_habilitado",
            "retencao_dias",
            "categoria",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "e2ee_habilitado"]

    def create(self, validated_data: dict[str, Any]) -> ChatChannel:
        request = self.context["request"]
        participantes_ids = self.initial_data.get("participantes") or []
        if isinstance(participantes_ids, str):  # pragma: no cover - defensive
            participantes_ids = [participantes_ids]
        participantes: Iterable[User] = User.objects.filter(id__in=participantes_ids)
        e2ee_habilitado = bool(self.initial_data.get("e2ee_habilitado", False))
        categoria = validated_data.pop("categoria", None)
        canal = criar_canal(
            criador=request.user,
            contexto_tipo=validated_data.get("contexto_tipo"),
            contexto_id=validated_data.get("contexto_id"),
            titulo=validated_data.get("titulo"),
            descricao=validated_data.get("descricao"),
            participantes=participantes,
            e2ee_habilitado=e2ee_habilitado,
        )
        if categoria:
            canal.categoria = categoria
            canal.save(update_fields=["categoria"])
        return canal

    def to_representation(self, instance: ChatChannel) -> dict[str, Any]:
        data = super().to_representation(instance)
        data["participantes"] = instance.participants.count()
        last_msg = instance.messages.select_related("remetente").order_by("-created").first()
        if last_msg:
            data["ultima_mensagem"] = ChatMessageSerializer(last_msg, context=self.context).data
        return data


class ChatAttachmentSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatAttachment
        fields = [
            "id",
            "filename",
            "mime_type",
            "tamanho",
            "thumb_url",
            "preview_url",
            "infected",
            "created",
        ]
        read_only_fields = fields

    def get_filename(self, obj: ChatAttachment) -> str:
        return obj.arquivo.name.rsplit("/", 1)[-1]

    def get_preview_url(self, obj: ChatAttachment) -> str:
        if not obj.infected and obj.preview_ready:
            request = self.context.get("request")
            url = obj.arquivo.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return ""


class ChatRetentionSerializer(serializers.Serializer):
    """Serializer para configuração de política de retenção."""

    retencao_dias = serializers.IntegerField(
        min_value=1,
        max_value=365,
        allow_null=True,
    )


class ChatMessageSerializer(serializers.ModelSerializer):
    remetente = serializers.PrimaryKeyRelatedField(read_only=True)
    reactions = serializers.SerializerMethodField()
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=ChatMessage.objects.all(),
        required=False,
        allow_null=True,
    )
    conteudo_cifrado = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "channel",
            "remetente",
            "tipo",
            "conteudo",
            "conteudo_cifrado",
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
        if channel.e2ee_habilitado:
            return enviar_mensagem(
                canal=channel,
                remetente=remetente,
                tipo=tipo,
                conteudo="",
                arquivo=arquivo,
                reply_to=reply_to,
                conteudo_cifrado=conteudo,
            )
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
        if instance.channel.e2ee_habilitado:
            data["conteudo_cifrado"] = instance.conteudo_cifrado
            data["conteudo"] = ""
        return data

    def get_reactions(self, obj: ChatMessage) -> dict[str, int]:
        return obj.reaction_counts()


class TrendingTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendingTopic
        fields = [
            "palavra",
            "frequencia",
            "periodo_inicio",
            "periodo_fim",
            "canal",
        ]
        read_only_fields = fields


class ChatNotificationSerializer(serializers.ModelSerializer):
    mensagem_conteudo = serializers.SerializerMethodField()
    canal_url = serializers.SerializerMethodField()
    canal_titulo = serializers.CharField(source="mensagem.channel.titulo", read_only=True)
    mensagem_tipo = serializers.CharField(source="mensagem.tipo", read_only=True)
    canal_id = serializers.CharField(source="mensagem.channel_id", read_only=True)
    reply_to = serializers.UUIDField(source="mensagem.reply_to_id", read_only=True, allow_null=True)

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
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_mensagem_conteudo(self, obj: ChatNotification) -> str:
        msg = obj.mensagem
        if msg.channel.e2ee_habilitado:
            return msg.conteudo_cifrado
        if msg.tipo == "text":
            return msg.conteudo
        return msg.conteudo or (msg.arquivo.url if msg.arquivo else "")

    def get_canal_url(self, obj: ChatNotification) -> str:
        request = self.context.get("request")
        url = obj.mensagem.channel.get_absolute_url()
        if request:
            return request.build_absolute_uri(url)
        return url


class ResumoChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumoChat
        fields = ["id", "periodo", "conteudo", "created_at", "detalhes"]


class UserChatPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChatPreference
        fields = [
            "id",
            "tema",
            "buscas_salvas",
            "resumo_diario",
            "resumo_semanal",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]
