from __future__ import annotations

from rest_framework import serializers

from .models import RespostaDiscussao, Tag, TopicoDiscussao


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "nome"]


class RespostaDiscussaoSerializer(serializers.ModelSerializer):
    autor_email = serializers.EmailField(source="autor.email", read_only=True)

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
            "created",
            "modified",
        ]
        read_only_fields = ["autor", "editado", "created", "modified", "editado_em"]


class TopicoDiscussaoSerializer(serializers.ModelSerializer):
    autor_email = serializers.EmailField(source="autor.email", read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    melhor_resposta = RespostaDiscussaoSerializer(read_only=True)

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
            "created",
            "modified",
        ]
        read_only_fields = ["autor", "numero_visualizacoes", "slug", "resolvido"]

    def create(self, validated_data: dict) -> TopicoDiscussao:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        topico = TopicoDiscussao.objects.create(**validated_data)
        if tags_data:
            topico.tags.set(Tag.objects.filter(pk__in=tags_data))
        return topico

    def update(self, instance: TopicoDiscussao, validated_data: dict) -> TopicoDiscussao:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        instance = super().update(instance, validated_data)
        if tags_data:
            instance.tags.set(Tag.objects.filter(pk__in=tags_data))
        return instance
