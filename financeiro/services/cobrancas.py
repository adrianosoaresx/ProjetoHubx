from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro, FinanceiroLog
from .notificacoes import enviar_cobranca
from .auditoria import log_financeiro
from . import metrics

logger = logging.getLogger(__name__)

try:
    from nucleos.models import ParticipacaoNucleo
except Exception:  # pragma: no cover - núcleo opcional
    ParticipacaoNucleo = None  # type: ignore


def _centro_organizacao() -> CentroCusto | None:
    """Retorna o centro de custo principal da organização."""
    return CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()


def _nucleos_do_usuario(user) -> Iterable[tuple[CentroCusto, Decimal]]:
    """Obtém centros de custo dos núcleos ativos do usuário e seus valores."""
    if not ParticipacaoNucleo:
        return []
    participacoes = getattr(user, "participacoes", None)
    if participacoes is None:
        return []
    result: list[tuple[CentroCusto, Decimal]] = []
    for part in participacoes.all():
        if part.status != "aprovado":
            continue
        nucleo = part.nucleo
        centro = nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
        if centro:
            val = getattr(nucleo, "mensalidade", getattr(settings, "MENSALIDADE_NUCLEO", Decimal("30.00")))
            result.append((centro, val))
    return result


def gerar_cobrancas() -> None:
    """Cria lançamentos de cobrança para associados e núcleos."""
    centro_org = _centro_organizacao()
    if not centro_org:
        return

    qs = ContaAssociado.objects.filter(user__is_active=True, user__is_associado=True).select_related("user")
    if ParticipacaoNucleo:
        qs = qs.prefetch_related(
            Prefetch(
                "user__participacoes",
                queryset=ParticipacaoNucleo.objects.select_related("nucleo").filter(status="aprovado"),
            )
        )

    lancamentos: list[LancamentoFinanceiro] = []
    now = timezone.now()
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    venc_dia = getattr(settings, "MENSALIDADE_VENCIMENTO_DIA", 10)
    data_venc = inicio_mes + timezone.timedelta(days=venc_dia - 1)
    val_assoc = getattr(settings, "MENSALIDADE_ASSOCIACAO", Decimal("50.00"))
    total = 0
    for conta in qs:
        if not LancamentoFinanceiro.objects.filter(
            centro_custo=centro_org,
            conta_associado=conta,
            tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            data_lancamento=inicio_mes,
        ).exists():
            lancamentos.append(
                LancamentoFinanceiro(
                    centro_custo=centro_org,
                    conta_associado=conta,
                    tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
                    valor=val_assoc,
                    data_lancamento=inicio_mes,
                    data_vencimento=data_venc,
                    status=LancamentoFinanceiro.Status.PENDENTE,
                    descricao="Cobrança mensalidade associação",
                )
            )
        for centro, val_nucleo in _nucleos_do_usuario(conta.user):
            if not LancamentoFinanceiro.objects.filter(
                centro_custo=centro,
                conta_associado=conta,
                tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO,
                data_lancamento=inicio_mes,
            ).exists():
                lancamentos.append(
                    LancamentoFinanceiro(
                        centro_custo=centro,
                        conta_associado=conta,
                        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO,
                        valor=val_nucleo,
                        data_lancamento=inicio_mes,
                        data_vencimento=data_venc,
                        status=LancamentoFinanceiro.Status.PENDENTE,
                        descricao=f"Cobrança mensalidade núcleo {centro.nucleo}",
                    )
                )

    with transaction.atomic():
        for lanc in lancamentos:
            lanc.save()
            total += 1
            log_financeiro(
                FinanceiroLog.Acao.CRIAR_COBRANCA,
                lanc.conta_associado.user,
                {},
                {"lancamento": str(lanc.id), "valor": str(lanc.valor)},
            )
            try:
                enviar_cobranca(lanc.conta_associado.user, lanc)
            except Exception as exc:  # pragma: no cover - integração externa
                logger.error("Falha ao notificar cobrança: %s", exc)
    if total:
        metrics.financeiro_cobrancas_total.inc(total)
