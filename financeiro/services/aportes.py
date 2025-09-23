from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import FinanceiroLog, LancamentoFinanceiro
from .auditoria import log_financeiro
from .notificacoes import enviar_estorno_aporte
from .saldos import aplicar_ajustes, debitar, vincular_carteiras_lancamento


def estornar_aporte(aporte_id: str, usuario=None) -> LancamentoFinanceiro:
    """Estorna um aporte pago, revertendo saldos e registrando auditoria."""

    lancamento = LancamentoFinanceiro.objects.select_related("centro_custo", "conta_associado").get(pk=aporte_id)
    if lancamento.tipo not in {
        LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        LancamentoFinanceiro.Tipo.APORTE_EXTERNO,
    }:
        raise ValidationError("Lançamento não é um aporte")
    if lancamento.status != LancamentoFinanceiro.Status.PAGO:
        raise ValidationError("Apenas aportes pagos podem ser estornados")

    with transaction.atomic():
        vincular_carteiras_lancamento(lancamento)
        LancamentoFinanceiro.objects.filter(pk=lancamento.pk).update(status=LancamentoFinanceiro.Status.CANCELADO)
        aplicar_ajustes(
            centro_custo=lancamento.centro_custo,
            carteira=lancamento.carteira,
            centro_delta=debitar(lancamento.valor),
            conta_associado=lancamento.conta_associado,
            carteira_contraparte=lancamento.carteira_contraparte,
            contraparte_delta=debitar(lancamento.valor) if lancamento.conta_associado_id else None,
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
