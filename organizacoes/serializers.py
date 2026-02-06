from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from accounts.models import UserType
from .models import (
    Organizacao,
    OrganizacaoAtividadeLog,
    OrganizacaoChangeLog,
    OrganizacaoRecurso,
)
from .tasks import organizacao_alterada
from .utils import validate_cnpj, validate_organizacao_image
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
            "tipo",
            "rua",
            "cidade",
            "estado",
            "cep",
            "contato_nome",
            "contato_email",
            "contato_telefone",
            "contato_whatsapp",
            "codigo_banco",
            "nome_banco",
            "agencia",
            "conta_corrente",
            "chave_pix",
            "valor_associacao",
            "valor_nucleacao",
            "dia_vencimento",
            "periodicidade",
            "nome_site",
            "site",
            "icone_site",
            "feed_noticias",
            "avatar",
            "inativa",
            "inativada_em",
            "created_by",
        ]
        read_only_fields = ["created_by", "inativada_em"]

    def create(self, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if validated_data.get("inativa"):
            validated_data["inativada_em"] = timezone.now()
        try:
            validated_data["cnpj"] = validate_cnpj(validated_data.get("cnpj"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"cnpj": exc.messages}) from exc
        instance = Organizacao(created_by=user, **validated_data)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
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
        payment_fields = {
            "mercado_pago_public_key",
            "mercado_pago_access_token",
            "mercado_pago_webhook_secret",
            "paypal_client_id",
            "paypal_client_secret",
            "paypal_webhook_secret",
        }
        if user and user.user_type != UserType.ROOT:
            forbidden_fields = payment_fields.intersection(validated_data.keys())
            if forbidden_fields:
                raise serializers.ValidationError(
                    {field: "Somente root pode atualizar este campo." for field in sorted(forbidden_fields)}
                )
        if "cnpj" in validated_data:
            try:
                validated_data["cnpj"] = validate_cnpj(validated_data["cnpj"])
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"cnpj": exc.messages}) from exc
        if "inativa" in validated_data:
            validated_data["inativada_em"] = timezone.now() if validated_data["inativa"] else None
        campos_relevantes = [
            "nome",
            "tipo",
            "cnpj",
            "contato_nome",
            "contato_email",
            "contato_telefone",
            "contato_whatsapp",
            "cep",
            "codigo_banco",
            "nome_banco",
            "agencia",
            "conta_corrente",
            "inativa",
            "chave_pix",
            "nome_site",
            "site",
            "icone_site",
            "feed_noticias",
            "valor_associacao",
            "valor_nucleacao",
            "dia_vencimento",
            "periodicidade",
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
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        instance.save()
        OrganizacaoAtividadeLog.objects.create(
            organizacao=instance,
            usuario=user,
            acao="updated",
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="updated")
        return instance

    def _validate_imagem(self, value):
        try:
            validate_organizacao_image(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_avatar(self, value):
        return self._validate_imagem(value)

    def validate_icone_site(self, value):
        return self._validate_imagem(value)


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
