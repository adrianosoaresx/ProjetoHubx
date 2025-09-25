from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import LancamentoFinanceiro
from .notificacoes import enviar_estorno_aporte
from .saldos import aplicar_ajustes, debitar, vincular_carteiras_lancamento


def estornar_aporte(aporte_id: str, usuario=None) -> LancamentoFinanceiro:
    """Estorna um aporte pago, revertendo saldos e registrando auditoria."""

    lancamento = (
        LancamentoFinanceiro.objects.select_related(
            "centro_custo",
            "conta_associado",
            "carteira",
            "carteira_contraparte__conta_associado",
        ).get(pk=aporte_id)
    )
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
        conta_destino = lancamento.conta_associado_resolvida
        aplicar_ajustes(
            centro_custo=lancamento.centro_custo,
            carteira=lancamento.carteira,
            centro_delta=debitar(lancamento.valor),
            conta_associado=conta_destino,
            carteira_contraparte=lancamento.carteira_contraparte,
            contraparte_delta=debitar(lancamento.valor) if conta_destino else None,
        )
        lancamento.status = LancamentoFinanceiro.Status.CANCELADO

    conta_destino = lancamento.conta_associado_resolvida
    if conta_destino:
        try:  # pragma: no cover - integração externa
            enviar_estorno_aporte(conta_destino.user, lancamento)
        except Exception:
            pass

    return lancamento
