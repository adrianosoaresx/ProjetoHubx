from __future__ import annotations

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    CategoriaDiscussao,
    Denuncia,
    DiscussionModerationLog,
    RespostaDiscussao,
    Tag,
    TopicoDiscussao,
)
from .services import denunciar_conteudo, DiscussaoError


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "nome", "slug"]


class CategoriaDiscussaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDiscussao
        fields = [
            "id",
            "nome",
            "slug",
            "descricao",
            "organizacao",
            "nucleo",
            "evento",
            "icone",
            "created_at",
            "updated_at",
        ]


class RespostaDiscussaoSerializer(serializers.ModelSerializer):
    autor_email = serializers.EmailField(source="autor.email", read_only=True)
    score = serializers.IntegerField(read_only=True)
    num_votos = serializers.IntegerField(read_only=True)

    class Meta:
        model = RespostaDiscussao
        fields = [
            "id",
            "topico",
            "autor",
            "autor_email",
            "conteudo",
            "arquivo",
            "reply_to",
            "editado",
            "editado_em",
            "motivo_edicao",
            "score",
            "num_votos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "autor",
            "editado",
            "created_at",
            "updated_at",
            "editado_em",
            "score",
            "num_votos",
        ]


class TopicoDiscussaoSerializer(serializers.ModelSerializer):
    autor_email = serializers.EmailField(source="autor.email", read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    melhor_resposta = RespostaDiscussaoSerializer(read_only=True)
    score = serializers.IntegerField(read_only=True)
    num_votos = serializers.IntegerField(read_only=True)

    class Meta:
        model = TopicoDiscussao
        fields = [
            "id",
            "categoria",
            "titulo",
            "slug",
            "conteudo",
            "autor",
            "autor_email",
            "publico_alvo",
            "tags",
            "fechado",
            "resolvido",
            "melhor_resposta",
            "numero_visualizacoes",
            "score",
            "num_votos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "autor",
            "numero_visualizacoes",
            "slug",
            "resolvido",
            "score",
            "num_votos",
        ]

    def create(self, validated_data: dict) -> TopicoDiscussao:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        topico = TopicoDiscussao.objects.create(**validated_data)
        if tags_data:
            topico.tags.set(Tag.objects.filter(slug__in=tags_data))
        return topico

    def update(self, instance: TopicoDiscussao, validated_data: dict) -> TopicoDiscussao:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        instance = super().update(instance, validated_data)
        if tags_data:
            instance.tags.set(Tag.objects.filter(slug__in=tags_data))
        return instance


class DiscussionModerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionModerationLog
        fields = ["id", "action", "moderator", "notes", "created_at"]
        read_only_fields = fields


class DenunciaSerializer(serializers.ModelSerializer):
    content_type_id = serializers.IntegerField(write_only=True)
    log = DiscussionModerationLogSerializer(read_only=True)

    class Meta:
        model = Denuncia
        fields = [
            "id",
            "user",
            "content_type_id",
            "object_id",
            "motivo",
            "status",
            "log",
            "created_at",
        ]
        read_only_fields = ["id", "user", "status", "log", "created_at"]

    def create(self, validated_data: dict) -> Denuncia:
        ct_id = validated_data.pop("content_type_id")
        try:
            ct = ContentType.objects.get(id=ct_id)
            obj = ct.get_object_for_this_type(id=validated_data["object_id"])
        except (ContentType.DoesNotExist, ObjectDoesNotExist):
            raise serializers.ValidationError({"object_id": "Objeto não encontrado."})
        request = self.context["request"]
        try:
            return denunciar_conteudo(
                user=request.user,
                content_object=obj,
                motivo=validated_data["motivo"],
            )
        except DiscussaoError as exc:  # pragma: no cover - defensive
            raise serializers.ValidationError({"detail": str(exc)})


class VotoDiscussaoSerializer(serializers.Serializer):
    content_type_id = serializers.IntegerField()
    object_id = serializers.IntegerField()
    valor = serializers.ChoiceField(choices=[1, -1])
