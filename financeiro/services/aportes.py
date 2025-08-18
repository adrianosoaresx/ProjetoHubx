from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro, FinanceiroLog
from .auditoria import log_financeiro
from .notificacoes import enviar_estorno_aporte


def estornar_aporte(aporte_id: str, usuario=None) -> LancamentoFinanceiro:
    """Estorna um aporte pago, revertendo saldos e registrando auditoria."""

    lancamento = LancamentoFinanceiro.objects.select_related("centro_custo", "conta_associado").get(
        pk=aporte_id
    )
    if lancamento.tipo not in {
        LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        LancamentoFinanceiro.Tipo.APORTE_EXTERNO,
    }:
        raise ValidationError("Lançamento não é um aporte")
    if lancamento.status != LancamentoFinanceiro.Status.PAGO:
        raise ValidationError("Apenas aportes pagos podem ser estornados")

    with transaction.atomic():
        LancamentoFinanceiro.objects.filter(pk=lancamento.pk).update(
            status=LancamentoFinanceiro.Status.CANCELADO
        )
        CentroCusto.objects.filter(pk=lancamento.centro_custo_id).update(
            saldo=F("saldo") - lancamento.valor
        )
        if lancamento.conta_associado_id:
            ContaAssociado.objects.filter(pk=lancamento.conta_associado_id).update(
                saldo=F("saldo") - lancamento.valor
            )
        lancamento.status = LancamentoFinanceiro.Status.CANCELADO

    log_financeiro(
        FinanceiroLog.Acao.EDITAR_LANCAMENTO,
        usuario,
        {"status": LancamentoFinanceiro.Status.PAGO},
        {"status": LancamentoFinanceiro.Status.CANCELADO, "id": str(lancamento.id)},
    )

    if lancamento.conta_associado:
        try:  # pragma: no cover - integração externa
            enviar_estorno_aporte(lancamento.conta_associado.user, lancamento)
        except Exception:
            pass

    return lancamento

