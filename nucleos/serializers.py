from __future__ import annotations

from rest_framework import serializers

from .models import ConviteNucleo, CoordenadorSuplente, Nucleo, ParticipacaoNucleo


class CoordenadorSuplenteSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = CoordenadorSuplente
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "periodo_inicio",
            "periodo_fim",
            "status",
        ]

    def get_status(self, obj: CoordenadorSuplente) -> str:
        return "ativo" if obj.ativo else "inativo"


class ParticipacaoNucleoSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ParticipacaoNucleo
        fields = [
            "id",
            "user",
            "user_email",
            "nucleo",
            "papel",
            "status",
            "status_suspensao",
            "data_suspensao",
            "data_solicitacao",
            "data_decisao",
            "decidido_por",
            "justificativa",
        ]
        read_only_fields = [
            "status",
            "status_suspensao",
            "data_solicitacao",
            "data_decisao",
            "decidido_por",
            "justificativa",
            "data_suspensao",
        ]


class NucleoSerializer(serializers.ModelSerializer):
    suplentes = CoordenadorSuplenteSerializer(many=True, read_only=True, source="coordenadores_suplentes")

    class Meta:
        model = Nucleo
        fields = [
            "id",
            "organizacao",
            "nome",
            "slug",
            "descricao",
            "avatar",
            "cover",
            "ativo",
            "created_at",
            "deleted",
            "deleted_at",
            "suplentes",
        ]
        read_only_fields = ["deleted", "deleted_at", "created_at"]


class ConviteNucleoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConviteNucleo
        fields = [
            "id",
            "token",
            "email",
            "papel",
            "nucleo",
            "limite_uso_diario",
            "data_expiracao",
            "usado_em",
            "created_at",
            "deleted",
            "deleted_at",
        ]
        read_only_fields = [
            "id",
            "token",
            "data_expiracao",
            "usado_em",
            "created_at",
            "deleted",
            "deleted_at",
        ]
