from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    FinanceiroTaskLog,
    LancamentoFinanceiro,
    ImportacaoPagamentos,
    IntegracaoConfig,
)
from ..services.distribuicao import repassar_receita_ingresso
from ..services.notificacoes import enviar_aporte


class CentroCustoSerializer(serializers.ModelSerializer):
    """Serializador do modelo :class:`CentroCusto`."""

    class Meta:
        model = CentroCusto
        fields = [
            "id",
            "nome",
            "tipo",
            "organizacao",
            "nucleo",
            "evento",
            "descricao",
            "saldo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["saldo", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        evento = attrs.get("evento", getattr(self.instance, "evento", None))
        if tipo == CentroCusto.Tipo.EVENTO:
            if not evento:
                raise serializers.ValidationError({"evento": _("Evento é obrigatório para centros do tipo evento")})
            if not attrs.get("nucleo") and getattr(evento, "nucleo_id", None):
                attrs["nucleo"] = evento.nucleo
        return attrs


class ContaAssociadoSerializer(serializers.ModelSerializer):
    """Serializador do modelo :class:`ContaAssociado`."""

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
    """Serializador de ``LancamentoFinanceiro``."""

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
            "origem",
            "lancamento_original",
            "ajustado",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Valida vencimento e valores."""
        data_lanc = attrs.get("data_lancamento", timezone.now())
        venc = attrs.get("data_vencimento")
        if venc and venc < data_lanc:
            raise serializers.ValidationError(_("Vencimento não pode ser anterior à data de lançamento"))
        valor = attrs.get("valor", getattr(self.instance, "valor", None))
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        if valor is not None and valor < 0 and tipo != LancamentoFinanceiro.Tipo.DESPESA:
            raise serializers.ValidationError({"valor": _("Valor negativo não permitido para este tipo")})
        return attrs

    def create(self, validated_data: dict[str, Any]) -> LancamentoFinanceiro:
        """Cria o lançamento e atualiza saldos se estiver pago."""
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
            if lancamento.tipo == LancamentoFinanceiro.Tipo.INGRESSO_EVENTO:
                repassar_receita_ingresso(lancamento)
        return lancamento


class AporteSerializer(serializers.ModelSerializer):
    """Serializador específico para criação de aportes."""

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
            "origem",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["originador", "origem", "created_at", "updated_at"]
        extra_kwargs = {"tipo": {"required": False}}

    def validate_valor(self, value: Any) -> Any:  # type: ignore[override]
        """Valida que o valor informado é positivo."""
        if value <= 0:
            raise serializers.ValidationError(_("Valor deve ser positivo"))
        return value

    def validate_tipo(self, value: str) -> str:  # type: ignore[override]
        """Garante que o tipo do aporte é permitido."""
        if value not in {
            LancamentoFinanceiro.Tipo.APORTE_INTERNO,
            LancamentoFinanceiro.Tipo.APORTE_EXTERNO,
        }:
            raise serializers.ValidationError(_("Tipo de aporte inválido"))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Preenche campos padrão do aporte."""
        if "tipo" not in attrs:
            attrs["tipo"] = LancamentoFinanceiro.Tipo.APORTE_INTERNO
        attrs.setdefault("status", LancamentoFinanceiro.Status.PAGO)
        return super().validate(attrs)

    def create(self, validated_data: dict[str, Any]) -> LancamentoFinanceiro:
        """Registra o aporte e atualiza os saldos."""
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
            centro = CentroCusto.objects.select_related(None).get(pk=lancamento.centro_custo_id)
            centro.saldo += lancamento.valor
            centro.save(update_fields=["saldo"])
            if lancamento.conta_associado_id:
                conta = ContaAssociado.objects.select_related(None).get(pk=lancamento.conta_associado_id)
                conta.saldo += lancamento.valor
                conta.save(update_fields=["saldo"])
        if lancamento.conta_associado:
            try:
                enviar_aporte(lancamento.conta_associado.user, lancamento)
            except Exception:  # pragma: no cover - integração externa
                pass
        return lancamento


class ImportarPagamentosPreviewSerializer(serializers.Serializer):
    """Valida o arquivo enviado para pré-visualização da importação."""

    file = serializers.FileField()

    def validate_file(self, file):  # type: ignore[override]
        """Aceita apenas arquivos CSV ou XLSX."""
        name = file.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):
            raise serializers.ValidationError(_("Formato inválido. Envie CSV ou XLSX"))
        return file


class ImportarPagamentosConfirmacaoSerializer(serializers.Serializer):
    """Valida o token de confirmação da importação."""

    id = serializers.CharField()
    importacao_id = serializers.UUIDField()


class ImportacaoPagamentosSerializer(serializers.ModelSerializer):
    """Serializador para ``ImportacaoPagamentos``."""

    class Meta:
        model = ImportacaoPagamentos
        fields = [
            "id",
            "arquivo",
            "data_importacao",
            "usuario",
            "total_processado",
            "erros",
            "status",
        ]
        read_only_fields = fields


class IntegracaoConfigSerializer(serializers.ModelSerializer):
    """Serializador para ``IntegracaoConfig``."""

    credenciais = serializers.CharField(source="credenciais_encrypted", allow_blank=True, required=False)

    class Meta:
        model = IntegracaoConfig
        fields = [
            "id",
            "nome",
            "tipo",
            "base_url",
            "credenciais",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class FinanceiroLogSerializer(serializers.ModelSerializer):
    """Serializador para registros de auditoria."""

    class Meta:
        model = FinanceiroLog
        fields = [
            "id",
            "usuario",
            "acao",
            "dados_anteriores",
            "dados_novos",
            "created_at",
        ]
        read_only_fields = fields


class FinanceiroTaskLogSerializer(serializers.ModelSerializer):
    """Serializador para logs de tarefas."""

    class Meta:
        model = FinanceiroTaskLog
        fields = [
            "id",
            "nome_tarefa",
            "executada_em",
            "status",
            "detalhes",
        ]
        read_only_fields = fields
