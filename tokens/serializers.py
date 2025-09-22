from __future__ import annotations

from rest_framework import serializers

from .models import TokenAcesso, TokenUsoLog


class TokenAcessoSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(read_only=True)
    revogado_por_email = serializers.EmailField(source="revogado_por.email", default=None, read_only=True)
    ip_gerado = serializers.IPAddressField(read_only=True, allow_null=True)
    ip_utilizado = serializers.IPAddressField(read_only=True, allow_null=True)

    class Meta:
        model = TokenAcesso
        fields = [
            "id",
            "codigo",
            "tipo_destino",
            "estado",
            "data_expiracao",
            "gerado_por",
            "usuario",
            "organizacao",
            "nucleos",
            "ip_gerado",
            "ip_utilizado",
            "revogado_em",
            "revogado_por",
            "revogado_por_email",
            "created_at",
        ]
        read_only_fields = [
            "codigo",
            "estado",
            "gerado_por",
            "usuario",
            "organizacao",
            "ip_gerado",
            "ip_utilizado",
            "revogado_em",
            "revogado_por",
            "created_at",
        ]


class TokenUsoLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", default=None)

    class Meta:
        model = TokenUsoLog
        fields = [
            "id",
            "token",
            "usuario_email",
            "acao",
            "ip",
            "user_agent",
            "created_at",
        ]
        read_only_fields = ["id", "token", "usuario_email", "created_at"]
