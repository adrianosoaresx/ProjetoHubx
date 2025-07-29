from __future__ import annotations

from django.db import transaction
from django.db.models import F

from ..models import CentroCusto, LancamentoFinanceiro


def repassar_receita_ingresso(lancamento: LancamentoFinanceiro) -> None:
    """Repasse automático da receita de ingressos."""
    if (
        lancamento.tipo != LancamentoFinanceiro.Tipo.INGRESSO_EVENTO
        or lancamento.status != LancamentoFinanceiro.Status.PAGO
    ):
        return

    centro_evento = lancamento.centro_custo
    nucleo = centro_evento.nucleo

    if nucleo:
        centro_nucleo = nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
        if not centro_nucleo:
            return
        with transaction.atomic():
            LancamentoFinanceiro.objects.create(
                centro_custo=centro_nucleo,
                tipo=LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                valor=lancamento.valor,
                data_lancamento=lancamento.data_lancamento,
                data_vencimento=lancamento.data_lancamento,
                status=LancamentoFinanceiro.Status.PAGO,
                descricao="Repasse de ingresso",
            )
            CentroCusto.objects.filter(pk=centro_nucleo.id).update(saldo=F("saldo") + lancamento.valor)
    else:
        centro_org = CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()
        if centro_org:
            with transaction.atomic():
                LancamentoFinanceiro.objects.create(
                    centro_custo=centro_org,
                    tipo=LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                    valor=lancamento.valor,
                    data_lancamento=lancamento.data_lancamento,
                    data_vencimento=lancamento.data_lancamento,
                    status=LancamentoFinanceiro.Status.PAGO,
                    descricao="Repasse de ingresso",
                )
                CentroCusto.objects.filter(pk=centro_org.id).update(saldo=F("saldo") + lancamento.valor)
