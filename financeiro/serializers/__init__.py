from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (
    Carteira,
    CentroCusto,
    ContaAssociado,
    LancamentoFinanceiro,
    ImportacaoPagamentos,
)
from ..services.notificacoes import enviar_aporte
from ..services.pagamentos import aplicar_pagamento_lancamento
from ..services.saldos import atribuir_carteiras_padrao


class CarteiraSerializer(serializers.ModelSerializer):
    """Serializador para o modelo :class:`Carteira`."""

    class Meta:
        model = Carteira
        fields = [
            "id",
            "centro_custo",
            "nome",
            "tipo",
            "descricao",
            "saldo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["saldo", "created_at", "updated_at"]


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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

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
    """Serializador do modelo legado :class:`ContaAssociado`."""

    legacy_warning = serializers.SerializerMethodField()

    class Meta:
        model = ContaAssociado
        fields = [
            "id",
            "user",
            "saldo",
            "created_at",
            "updated_at",
            "legacy_warning",
        ]
        read_only_fields = ["saldo", "created_at", "updated_at"]

    def get_legacy_warning(self, obj: ContaAssociado) -> str:  # pragma: no cover - getter simples
        return ContaAssociado.LEGACY_MESSAGE


class LancamentoFinanceiroSerializer(serializers.ModelSerializer):
    """Serializador de ``LancamentoFinanceiro``."""

    carteira = CarteiraSerializer(read_only=True)
    carteira_id = serializers.PrimaryKeyRelatedField(
        source="carteira",
        queryset=Carteira.objects.all(),
        required=False,
        allow_null=True,
    )
    carteira_contraparte = CarteiraSerializer(read_only=True)
    carteira_contraparte_id = serializers.PrimaryKeyRelatedField(
        source="carteira_contraparte",
        queryset=Carteira.objects.all(),
        required=False,
        allow_null=True,
    )
    conta_associado = serializers.PrimaryKeyRelatedField(
        queryset=ContaAssociado.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
        help_text=_("Campo legado; prefira informar carteira_contraparte_id."),
    )
    legacy_warning = serializers.SerializerMethodField()

    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id",
            "centro_custo",
            "conta_associado",
            "carteira_id",
            "carteira",
            "carteira_contraparte_id",
            "carteira_contraparte",
            "tipo",
            "valor",
            "data_lancamento",
            "data_vencimento",
            "status",
            "descricao",
            "origem",
            "lancamento_original",
            "ajustado",
            "legacy_warning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "carteira",
            "carteira_contraparte",
            "legacy_warning",
            "created_at",
            "updated_at",
        ]

    def _normalize_conta_associado(self, attrs: dict[str, Any]) -> dict[str, Any]:
        conta = attrs.get("conta_associado")
        carteira_contra = attrs.get("carteira_contraparte")
        if conta:
            self._legacy_input_used = True
        if carteira_contra and getattr(carteira_contra, "conta_associado_id", None):
            carteira_conta = carteira_contra.conta_associado
            if conta and carteira_conta and carteira_conta.id != conta.id:
                raise serializers.ValidationError(
                    {"carteira_contraparte_id": _("Carteira não pertence ao associado informado.")}
                )
            attrs.setdefault("conta_associado", carteira_conta)
        return attrs

    def get_legacy_warning(self, obj: LancamentoFinanceiro) -> str:
        if getattr(obj, "conta_associado_id", None):
            return ContaAssociado.LEGACY_MESSAGE
        if getattr(obj, "_legacy_input_used", False):  # pragma: no cover - fallback
            return ContaAssociado.LEGACY_MESSAGE
        return ""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Valida vencimento, valores e normaliza carteiras."""

        attrs = self._normalize_conta_associado(attrs)
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
        atribuir_carteiras_padrao(validated_data)
        lancamento = super().create(validated_data)
        if getattr(self, "_legacy_input_used", False):
            setattr(lancamento, "_legacy_input_used", True)
        if lancamento.status == LancamentoFinanceiro.Status.PAGO:
            aplicar_pagamento_lancamento(lancamento)
        return lancamento


class AporteSerializer(LancamentoFinanceiroSerializer):
    """Serializador específico para criação de aportes."""

    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id",
            "centro_custo",
            "conta_associado",
            "carteira_id",
            "carteira",
            "carteira_contraparte_id",
            "carteira_contraparte",
            "tipo",
            "valor",
            "data_lancamento",
            "data_vencimento",
            "status",
            "descricao",
            "originador",
            "origem",
            "legacy_warning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "originador",
            "origem",
            "carteira",
            "carteira_contraparte",
            "legacy_warning",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"tipo": {"required": False}}

    def validate_valor(self, value: Any) -> Any:  # type: ignore[override]
        """Garante que o valor não seja negativo."""
        if value < 0:
            raise serializers.ValidationError(_("Valor não pode ser negativo"))
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
        atribuir_carteiras_padrao(validated_data)
        with transaction.atomic():
            originador = None
            if tipo == LancamentoFinanceiro.Tipo.APORTE_INTERNO and request:
                originador = request.user
            validated_data["originador"] = originador
            lancamento = super().create(validated_data)
        if getattr(self, "_legacy_input_used", False):
            setattr(lancamento, "_legacy_input_used", True)
        conta_destino = lancamento.conta_associado_resolvida
        if conta_destino:
            try:
                enviar_aporte(conta_destino.user, lancamento)
            except Exception:  # pragma: no cover - integração externa
                pass
        return lancamento


class ImportarPagamentosPreviewSerializer(serializers.Serializer):
    """Valida o arquivo enviado para pré-visualização da importação."""

    MAX_FILE_SIZE_MB = 5

    file = serializers.FileField(help_text=_("Arquivo CSV ou XLSX até %(size)dMB") % {"size": MAX_FILE_SIZE_MB})

    def validate_file(self, file):  # type: ignore[override]
        """Aceita apenas arquivos CSV ou XLSX."""
        name = file.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):
            raise serializers.ValidationError(_("Formato inválido. Envie CSV ou XLSX"))
        max_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024
        if file.size > max_bytes:
            raise serializers.ValidationError(_("Arquivo maior que %(size)dMB") % {"size": self.MAX_FILE_SIZE_MB})
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


