from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro, FinanceiroLog
from .auditoria import log_financeiro
from .notificacoes import enviar_ajuste


def ajustar_lancamento(
    lancamento_id: str, valor_corrigido: Decimal, descricao_motivo: str, usuario=None
) -> LancamentoFinanceiro:
    """Realiza ajuste em um lançamento pago."""
    lancamento = LancamentoFinanceiro.objects.select_related("centro_custo", "conta_associado").get(pk=lancamento_id)
    if lancamento.status != LancamentoFinanceiro.Status.PAGO or lancamento.ajustado:
        raise ValidationError("Lançamento não pode ser ajustado")

    delta = valor_corrigido - lancamento.valor
    with transaction.atomic():
        ajuste = LancamentoFinanceiro.objects.create(
            centro_custo=lancamento.centro_custo,
            conta_associado=lancamento.conta_associado,
            tipo=LancamentoFinanceiro.Tipo.AJUSTE,
            valor=delta,
            data_lancamento=timezone.now(),
            data_vencimento=timezone.now(),
            status=LancamentoFinanceiro.Status.PAGO,
            descricao=descricao_motivo,
            lancamento_original=lancamento,
        )
        CentroCusto.objects.filter(pk=lancamento.centro_custo_id).update(saldo=F("saldo") + delta)
        if lancamento.conta_associado_id:
            ContaAssociado.objects.filter(pk=lancamento.conta_associado_id).update(saldo=F("saldo") + delta)
        lancamento.ajustado = True
        lancamento.save(update_fields=["ajustado"])
    log_financeiro(
        FinanceiroLog.Acao.AJUSTE_LANCAMENTO,
        usuario,
        {"valor": str(lancamento.valor)},
        {"valor_corrigido": str(valor_corrigido), "delta": str(delta)},
    )
    if lancamento.conta_associado:
        enviar_ajuste(lancamento.conta_associado.user, lancamento, delta)
    return ajuste
