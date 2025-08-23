from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import (
    Organizacao,
    OrganizacaoAtividadeLog,
    OrganizacaoChangeLog,
    OrganizacaoRecurso,
)
from .tasks import organizacao_alterada
from .utils import validate_cnpj
from feed.models import FeedPluginConfig


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
            "rate_limit_multiplier",
            "indice_reajuste",
            "inativa",
            "inativada_em",
            "created_by",
        ]
        read_only_fields = ["created_by", "inativada_em"]
        extra_kwargs = {"slug": {"required": False}}

    def validate_rate_limit_multiplier(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError(_("Deve ser maior que zero."))
        return value

    def validate_indice_reajuste(self, value: Decimal) -> Decimal:
        if not (Decimal("0") <= value <= Decimal("1")):
            raise serializers.ValidationError(_("Deve ser entre 0 e 1."))
        return value

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
        if validated_data.get("inativa"):
            validated_data["inativada_em"] = timezone.now()
        try:
            validated_data["cnpj"] = validate_cnpj(validated_data.get("cnpj"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"cnpj": exc.messages}) from exc
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
        if "inativa" in validated_data:
            validated_data["inativada_em"] = timezone.now() if validated_data["inativa"] else None
        campos_relevantes = [
            "nome",
            "tipo",
            "slug",
            "cnpj",
            "contato_nome",
            "contato_email",
            "inativa",
            "rate_limit_multiplier",
            "indice_reajuste",
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
    detalhes = serializers.JSONField(default=dict)

    class Meta:
        model = OrganizacaoAtividadeLog
        fields = [
            "id",
            "acao",
            "detalhes",
            "created_at",
            "usuario_email",
        ]


class FeedPluginConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedPluginConfig
        fields = [
            "id",
            "module_path",
            "frequency",
            "organizacao",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["organizacao", "created_at", "updated_at"]


class OrganizacaoRecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizacaoRecurso
        fields = ["id", "content_type", "object_id", "organizacao"]
        read_only_fields = ["id", "organizacao"]

    def validate(self, attrs):
        ct = attrs.get("content_type")
        obj_id = attrs.get("object_id")
        model_class = ct.model_class() if ct else None
        if model_class is None or not model_class.objects.filter(pk=obj_id).exists():
            raise serializers.ValidationError({"object_id": "Objeto não encontrado."})
        return attrs
