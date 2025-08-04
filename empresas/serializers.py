from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AvaliacaoEmpresa, Empresa, EmpresaChangeLog, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "nome", "categoria"]


class EmpresaSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = Empresa
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "organizacao",
            "nome",
            "cnpj",
            "tipo",
            "municipio",
            "estado",
            "logo",
            "descricao",
            "palavras_chave",
            "tags",
            "deleted",
        ]
        read_only_fields = ["deleted"]

    def create(self, validated_data: dict) -> Empresa:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        empresa = Empresa.objects.create(**validated_data)
        if tags_data:
            empresa.tags.set(Tag.objects.filter(pk__in=tags_data))
        return empresa

    def update(self, instance: Empresa, validated_data: dict) -> Empresa:
        request = self.context.get("request")
        tags_data = request.data.getlist("tags") if request else []
        old_values = {field: getattr(instance, field) for field in validated_data}
        instance = super().update(instance, validated_data)
        if tags_data:
            instance.tags.set(Tag.objects.filter(pk__in=tags_data))
        for field, old in old_values.items():
            new = getattr(instance, field)
            if old != new:
                EmpresaChangeLog.objects.create(
                    empresa=instance,
                    usuario=getattr(request, "user", None),
                    campo_alterado=field,
                    valor_antigo=old,
                    valor_novo=new,
                )
        return instance


class EmpresaChangeLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", default=None)

    class Meta:
        model = EmpresaChangeLog
        fields = [
            "id",
            "campo_alterado",
            "valor_antigo",
            "valor_novo",
            "alterado_em",
            "usuario_email",
        ]


class AvaliacaoEmpresaSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = AvaliacaoEmpresa
        fields = [
            "id",
            "empresa",
            "usuario",
            "usuario_email",
            "nota",
            "comentario",
            "created",
            "modified",
        ]
        read_only_fields = ["empresa", "usuario", "created", "modified"]
