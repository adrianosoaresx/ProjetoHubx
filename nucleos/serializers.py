from __future__ import annotations

from rest_framework import serializers

from .models import CoordenadorSuplente, Nucleo, ParticipacaoNucleo, ConviteNucleo


class CoordenadorSuplenteSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta:
        model = CoordenadorSuplente
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "inicio",
            "fim",
        ]


class ParticipacaoNucleoSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ParticipacaoNucleo
        fields = [
            "id",
            "user",
            "user_email",
            "nucleo",
            "is_coordenador",
            "status",
            "data_solicitacao",
            "data_decisao",
            "decidido_por",
        ]
        read_only_fields = [
            "status",
            "data_solicitacao",
            "data_decisao",
            "decidido_por",
        ]


class NucleoSerializer(serializers.ModelSerializer):
    suplentes = CoordenadorSuplenteSerializer(many=True, read_only=True, source="coordenadores_suplentes")

    class Meta:
        model = Nucleo
        fields = [
            "id",
            "organizacao",
            "nome",
            "descricao",
            "avatar",
            "cover",
            "created_at",
            "deleted",
            "deleted_at",
            "suplentes",
        ]
        read_only_fields = ["deleted", "deleted_at", "created_at"]


class ConviteNucleoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConviteNucleo
        fields = ["id", "token", "email", "papel", "nucleo", "usado_em", "criado_em"]
        read_only_fields = ["id", "token", "usado_em", "criado_em"]
