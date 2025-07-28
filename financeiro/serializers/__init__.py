from __future__ import annotations

from typing import Any

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
            "user_id",
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
            "status",
            "descricao",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data: dict[str, Any]) -> LancamentoFinanceiro:
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
