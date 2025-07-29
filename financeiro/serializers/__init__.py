from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
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


class AporteSerializer(serializers.ModelSerializer):
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
            "originador",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["originador", "created_at", "updated_at"]
        extra_kwargs = {"tipo": {"required": False}}

    def validate_valor(self, value: Any) -> Any:  # type: ignore[override]
        if value <= 0:
            raise serializers.ValidationError(_("Valor deve ser positivo"))
        return value

    def validate_tipo(self, value: str) -> str:  # type: ignore[override]
        if value not in {
            LancamentoFinanceiro.Tipo.APORTE_INTERNO,
            LancamentoFinanceiro.Tipo.APORTE_EXTERNO,
        }:
            raise serializers.ValidationError(_("Tipo de aporte inválido"))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if "tipo" not in attrs:
            attrs["tipo"] = LancamentoFinanceiro.Tipo.APORTE_INTERNO
        attrs.setdefault("status", LancamentoFinanceiro.Status.PAGO)
        return super().validate(attrs)

    def create(self, validated_data: dict[str, Any]) -> LancamentoFinanceiro:
        request = self.context.get("request")
        tipo = validated_data.get("tipo", LancamentoFinanceiro.Tipo.APORTE_INTERNO)
        if "data_lancamento" not in validated_data:
            validated_data["data_lancamento"] = timezone.now()
        if "data_vencimento" not in validated_data:
            validated_data["data_vencimento"] = validated_data["data_lancamento"]
        with transaction.atomic():
            originador = None
            if tipo == LancamentoFinanceiro.Tipo.APORTE_INTERNO and request:
                originador = request.user
            validated_data["originador"] = originador
            lancamento = super().create(validated_data)
            centro = (
                CentroCusto.objects.select_related(None).get(pk=lancamento.centro_custo_id)
            )
            centro.saldo += lancamento.valor
            centro.save(update_fields=["saldo"])
            if lancamento.conta_associado_id:
                conta = ContaAssociado.objects.select_related(None).get(pk=lancamento.conta_associado_id)
                conta.saldo += lancamento.valor
                conta.save(update_fields=["saldo"])
        return lancamento


class ImportarPagamentosPreviewSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):  # type: ignore[override]
        name = file.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):
            raise serializers.ValidationError("Formato inválido. Envie CSV ou XLSX")
        return file


class ImportarPagamentosConfirmacaoSerializer(serializers.Serializer):
    id = serializers.CharField()
