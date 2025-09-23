from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import FinanceiroLog, LancamentoFinanceiro
from .auditoria import log_financeiro
from .notificacoes import enviar_ajuste
from .saldos import aplicar_ajustes, vincular_carteiras_lancamento


def ajustar_lancamento(
    lancamento_id: str, valor_corrigido: Decimal, descricao_motivo: str, usuario=None
) -> LancamentoFinanceiro:
    """Realiza ajuste em um lançamento pago."""
    lancamento = LancamentoFinanceiro.objects.select_related("centro_custo", "conta_associado").get(pk=lancamento_id)
    if lancamento.status != LancamentoFinanceiro.Status.PAGO or lancamento.ajustado:
        raise ValidationError("Lançamento não pode ser ajustado")

    delta = valor_corrigido - lancamento.valor
    with transaction.atomic():
        vincular_carteiras_lancamento(lancamento)
        ajuste = LancamentoFinanceiro.objects.create(
            centro_custo=lancamento.centro_custo,
            conta_associado=lancamento.conta_associado,
            carteira=lancamento.carteira,
            carteira_contraparte=lancamento.carteira_contraparte,
            tipo=LancamentoFinanceiro.Tipo.AJUSTE,
            valor=delta,
            data_lancamento=timezone.now(),
            data_vencimento=timezone.now(),
            status=LancamentoFinanceiro.Status.PAGO,
            descricao=descricao_motivo,
            lancamento_original=lancamento,
        )
        aplicar_ajustes(
            centro_custo=lancamento.centro_custo,
            carteira=lancamento.carteira,
            centro_delta=delta,
            conta_associado=lancamento.conta_associado,
            carteira_contraparte=lancamento.carteira_contraparte,
            contraparte_delta=delta if lancamento.conta_associado_id else None,
        )
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
