from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework import serializers

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro


class CentroCustoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroCusto
        fields = [
            "id",
            "nome",
            "tipo",
            "organizacao",
            "nucleo",
            "evento",
            "saldo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["saldo", "created_at", "updated_at"]


class ContaAssociadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContaAssociado
        fields = [
            "id",
            "user",
            "saldo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["saldo", "created_at", "updated_at"]


class LancamentoFinanceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id",
            "centro_custo",
            "conta_associado",
            "tipo",
            "valor",
            "data_lancamento",
            "data_vencimento",
            "status",
            "descricao",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data_lanc = attrs.get("data_lancamento", timezone.now())
        venc = attrs.get("data_vencimento")
        if venc and venc < data_lanc:
            raise serializers.ValidationError("Vencimento não pode ser anterior à data de lançamento")
        return attrs

    def create(self, validated_data: dict[str, Any]) -> LancamentoFinanceiro:
        if "data_vencimento" not in validated_data:
            validated_data["data_vencimento"] = validated_data.get("data_lancamento", timezone.now())
        lancamento = super().create(validated_data)
        if lancamento.status == LancamentoFinanceiro.Status.PAGO:
            centro = lancamento.centro_custo
            centro.saldo += lancamento.valor
            centro.save(update_fields=["saldo"])
            if lancamento.conta_associado:
                conta = lancamento.conta_associado
                conta.saldo += lancamento.valor
                conta.save(update_fields=["saldo"])
        return lancamento


class ImportarPagamentosSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):  # type: ignore[override]
        name = file.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):
            raise serializers.ValidationError("Formato inválido. Envie CSV ou XLSX")
        return file
