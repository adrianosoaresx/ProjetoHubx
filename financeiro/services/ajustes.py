from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import LancamentoFinanceiro
from .notificacoes import enviar_ajuste
from .saldos import aplicar_ajustes, vincular_carteiras_lancamento


def ajustar_lancamento(
    lancamento_id: str, valor_corrigido: Decimal, descricao_motivo: str, usuario=None
) -> LancamentoFinanceiro:
    """Realiza ajuste em um lançamento pago."""
    lancamento = (
        LancamentoFinanceiro.objects.select_related(
            "centro_custo",
            "conta_associado",
            "carteira",
            "carteira_contraparte__conta_associado",
        ).get(pk=lancamento_id)
    )
    if lancamento.status != LancamentoFinanceiro.Status.PAGO or lancamento.ajustado:
        raise ValidationError("Lançamento não pode ser ajustado")

    delta = valor_corrigido - lancamento.valor
    with transaction.atomic():
        vincular_carteiras_lancamento(lancamento)
        conta_destino = lancamento.conta_associado_resolvida
        ajuste = LancamentoFinanceiro.objects.create(
            centro_custo=lancamento.centro_custo,
            conta_associado=conta_destino,
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
            conta_associado=conta_destino,
            carteira_contraparte=lancamento.carteira_contraparte,
            contraparte_delta=delta if conta_destino else None,
        )
        lancamento.ajustado = True
        lancamento.save(update_fields=["ajustado"])
    conta_destino = lancamento.conta_associado_resolvida
    if conta_destino:
        enviar_ajuste(conta_destino.user, lancamento, delta)
    return ajuste
