from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from agenda.models import Evento

from ..models import CentroCusto, LancamentoFinanceiro, FinanceiroLog
from .auditoria import log_financeiro
from .notificacoes import enviar_distribuicao


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


def distribuir_receita_evento(evento_id, valor: Decimal, conta_associado) -> None:
    """Distribui receita de um evento para os centros de custo apropriados."""
    evento = Evento.objects.select_related("nucleo").get(pk=evento_id)
    if evento.status not in {0, 1}:
        raise ValidationError("Evento não permite distribuição de receita")
    valor = Decimal(valor)
    with transaction.atomic():
        if evento.nucleo:
            centro_nucleo = evento.nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
            if not centro_nucleo:
                raise ValidationError("Núcleo sem centro de custo")
            lanc = LancamentoFinanceiro.objects.create(
                centro_custo=centro_nucleo,
                conta_associado=conta_associado,
                tipo=LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                valor=valor,
                data_lancamento=timezone.now(),
                data_vencimento=timezone.now(),
                status=LancamentoFinanceiro.Status.PAGO,
                descricao=f"Receita evento {evento.titulo}",
            )
            CentroCusto.objects.filter(pk=centro_nucleo.id).update(saldo=F("saldo") + valor)
            log_financeiro(
                FinanceiroLog.Acao.DISTRIBUIR_RECEITA,
                None,
                {},
                {"lancamento": str(lanc.id), "valor": str(valor)},
            )
            for coord in evento.nucleo.coordenadores:
                enviar_distribuicao(coord, evento, valor)
        else:
            centro_evento = evento.centros_custo.filter(tipo=CentroCusto.Tipo.EVENTO).order_by("created_at").first()
            centro_org = CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()
            if not centro_evento or not centro_org:
                raise ValidationError("Centros de custo indisponíveis")
            metade = valor / 2
            lanc_e = LancamentoFinanceiro.objects.create(
                centro_custo=centro_evento,
                conta_associado=conta_associado,
                tipo=LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                valor=metade,
                data_lancamento=timezone.now(),
                data_vencimento=timezone.now(),
                status=LancamentoFinanceiro.Status.PAGO,
                descricao=f"Receita evento {evento.titulo}",
            )
            lanc_o = LancamentoFinanceiro.objects.create(
                centro_custo=centro_org,
                conta_associado=conta_associado,
                tipo=LancamentoFinanceiro.Tipo.INGRESSO_EVENTO,
                valor=metade,
                data_lancamento=timezone.now(),
                data_vencimento=timezone.now(),
                status=LancamentoFinanceiro.Status.PAGO,
                descricao=f"Receita evento {evento.titulo}",
            )
            CentroCusto.objects.filter(pk=centro_evento.id).update(saldo=F("saldo") + metade)
            CentroCusto.objects.filter(pk=centro_org.id).update(saldo=F("saldo") + metade)
            log_financeiro(
                FinanceiroLog.Acao.DISTRIBUIR_RECEITA,
                None,
                {},
                {"lancamentos": [str(lanc_e.id), str(lanc_o.id)], "valor": str(valor)},
            )
            enviar_distribuicao(evento.coordenador, evento, valor)
