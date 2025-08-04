from __future__ import annotations

from rest_framework import serializers

from .models import Organizacao, OrganizacaoLog
from .tasks import organizacao_alterada


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
        instance = Organizacao.objects.create(created_by=user, **validated_data)
        OrganizacaoLog.objects.create(
            organizacao=instance,
            usuario=user,
            acao="created",
            dados_antigos={},
            dados_novos=validated_data,
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="created")
        return instance

    def update(self, instance: Organizacao, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        old_data = {k: getattr(instance, k) for k in validated_data}
        instance = super().update(instance, validated_data)
        user = getattr(request, "user", None)
        OrganizacaoLog.objects.create(
            organizacao=instance,
            usuario=user,
            acao="updated",
            dados_antigos=old_data,
            dados_novos=validated_data,
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="updated")
        return instance


class OrganizacaoLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", default=None)

    class Meta:
        model = OrganizacaoLog
        fields = [
            "id",
            "acao",
            "dados_antigos",
            "dados_novos",
            "created",
            "usuario_email",
        ]
