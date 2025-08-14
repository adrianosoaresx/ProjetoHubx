from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from .models import (
    Organizacao,
    OrganizacaoAtividadeLog,
    OrganizacaoChangeLog,
)
from .tasks import organizacao_alterada
from .utils import validate_cnpj


class OrganizacaoSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Organizacao
        fields = [
            "id",
            "nome",
            "cnpj",
            "descricao",
            "slug",
            "tipo",
            "rua",
            "cidade",
            "estado",
            "contato_nome",
            "contato_email",
            "contato_telefone",
            "avatar",
            "cover",
            "inativa",
            "inativada_em",
            "created_by",
        ]
        read_only_fields = ["inativada_em", "inativa", "created_by"]

    def create(self, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        slug = validated_data.get("slug")
        nome = validated_data.get("nome")
        slug = slugify(slug or nome)
        base = slug
        counter = 2
        while Organizacao.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        validated_data["slug"] = slug
        validated_data["cnpj"] = validate_cnpj(validated_data.get("cnpj"))
        instance = Organizacao(created_by=user, **validated_data)
        instance.full_clean()
        instance.save()
        OrganizacaoAtividadeLog.objects.create(
            organizacao=instance,
            usuario=user,
            acao="created",
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="created")
        return instance

    def update(self, instance: Organizacao, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if "cnpj" in validated_data:
            validated_data["cnpj"] = validate_cnpj(validated_data["cnpj"])
        if "slug" in validated_data or "nome" in validated_data:
            slug = validated_data.get("slug")
            nome = validated_data.get("nome", instance.nome)
            slug = slugify(slug or nome)
            base = slug
            counter = 2
            while Organizacao.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            validated_data["slug"] = slug
        campos_relevantes = [
            "nome",
            "tipo",
            "slug",
            "cnpj",
            "contato_nome",
            "contato_email",
        ]
        for campo in campos_relevantes:
            if campo in validated_data:
                antigo = getattr(instance, campo)
                novo = validated_data[campo]
                if antigo != novo:
                    OrganizacaoChangeLog.objects.create(
                        organizacao=instance,
                        campo_alterado=campo,
                        valor_antigo=str(antigo),
                        valor_novo=str(novo),
                        alterado_por=user,
                    )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        OrganizacaoAtividadeLog.objects.create(
            organizacao=instance,
            usuario=user,
            acao="updated",
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="updated")
        return instance


class OrganizacaoChangeLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="alterado_por.email", default=None)

    class Meta:
        model = OrganizacaoChangeLog
        fields = [
            "id",
            "campo_alterado",
            "valor_antigo",
            "valor_novo",
            "created_at",
            "usuario_email",
        ]


class OrganizacaoAtividadeLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", default=None)

    class Meta:
        model = OrganizacaoAtividadeLog
        fields = [
            "id",
            "acao",
            "detalhes",
            "created_at",
            "usuario_email",
        ]
