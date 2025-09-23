"""Helpers para processamento de pagamentos de lançamentos."""

from __future__ import annotations

from ..models import LancamentoFinanceiro
from .distribuicao import repassar_receita_ingresso
from .saldos import aplicar_ajustes, vincular_carteiras_lancamento


def aplicar_pagamento_lancamento(
    lancamento: LancamentoFinanceiro,
    *,
    status_anterior: str | None = None,
) -> bool:
    """Aplica ajustes de pagamento garantindo idempotência."""

    if lancamento.status != LancamentoFinanceiro.Status.PAGO:
        return False
    if status_anterior == LancamentoFinanceiro.Status.PAGO:
        return False

    vincular_carteiras_lancamento(lancamento)
    conta_destino = lancamento.conta_associado_resolvida
    contraparte_delta = lancamento.valor if conta_destino else None
    aplicar_ajustes(
        centro_custo=lancamento.centro_custo,
        carteira=lancamento.carteira,
        centro_delta=lancamento.valor,
        conta_associado=conta_destino,
        carteira_contraparte=lancamento.carteira_contraparte,
        contraparte_delta=contraparte_delta,
    )
    if lancamento.tipo == LancamentoFinanceiro.Tipo.INGRESSO_EVENTO:
        repassar_receita_ingresso(lancamento)
    return True
