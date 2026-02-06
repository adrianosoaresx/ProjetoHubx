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
    id = serializers.CharField(read_only=True)
    suplentes = CoordenadorSuplenteSerializer(many=True, read_only=True, source="coordenadores_suplentes")
    mensalidade = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Nucleo
        fields = [
            "id",
            "organizacao",
            "nome",
            "descricao",
            "classificacao",
            "avatar",
            "cover",
            "mensalidade",
            "ativo",
            "created_at",
            "deleted",
            "deleted_at",
            "suplentes",
        ]
        read_only_fields = ["deleted", "deleted_at", "created_at", "organizacao"]

    def validate_mensalidade(self, valor):
        if valor is not None and valor < 0:
            raise serializers.ValidationError("Valor inválido")
        return valor

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("mensalidade") in (None, ""):
            data["mensalidade"] = str(instance.mensalidade_efetiva)
        return data


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
