from rest_framework import serializers

from .models import AccountToken, User


class UserSerializer(serializers.ModelSerializer):
    tipo_usuario = serializers.CharField(source="get_tipo_usuario", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "cnpj",
            "razao_social",
            "nome_fantasia",
            "is_associado",
            "is_coordenador",
            "nucleo_id",
            "organizacao_id",
            "tipo_usuario",
            "deleted",
            "deleted_at",
            "two_factor_enabled",
        ]


class AccountTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountToken
        fields = [
            "codigo",
            "tipo",
            "usuario",
            "expires_at",
            "used_at",
        ]
        read_only_fields = ["codigo", "usuario", "used_at"]
