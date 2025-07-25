from __future__ import annotations

from rest_framework import serializers

from .models import Organizacao, OrganizacaoLog
from .tasks import organizacao_alterada


class OrganizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organizacao
        fields = [
            "id",
            "nome",
            "cnpj",
            "descricao",
            "slug",
            "avatar",
            "cover",
            "inativa",
            "inativada_em",
        ]
        read_only_fields = ["inativada_em", "inativa"]

    def create(self, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        instance = super().create(validated_data)
        OrganizacaoLog.objects.create(
            organizacao=instance,
            usuario=getattr(request, "user", None),
            acao="criacao",
            dados_antigos={},
            dados_novos=validated_data,
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="criacao")
        return instance

    def update(self, instance: Organizacao, validated_data: dict) -> Organizacao:
        request = self.context.get("request")
        old_data = {k: getattr(instance, k) for k in validated_data}
        instance = super().update(instance, validated_data)
        OrganizacaoLog.objects.create(
            organizacao=instance,
            usuario=getattr(request, "user", None),
            acao="atualizacao",
            dados_antigos=old_data,
            dados_novos=validated_data,
        )
        organizacao_alterada.send(sender=self.__class__, organizacao=instance, acao="atualizacao")
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
            "created_at",
            "usuario_email",
        ]
