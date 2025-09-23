from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro, FinanceiroLog
from .notificacoes import enviar_cobranca
from .auditoria import log_financeiro
from . import metrics
from .saldos import atribuir_carteiras_padrao

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
        if part.status != "ativo":
            continue
        nucleo = part.nucleo
        centro = nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
        if centro:
            val = getattr(nucleo, "mensalidade", getattr(settings, "MENSALIDADE_NUCLEO", Decimal("30.00")))
            result.append((centro, val))
    return result


def gerar_cobrancas(reajuste: Decimal | None = None) -> None:
    """Cria lançamentos de cobrança para associados e núcleos.

    Parâmetros:
        reajuste: percentual adicional (ex: 0.1 para 10%). Caso ``None``, utiliza o
        índice configurado na organização, se disponível.
    """
    centro_org = _centro_organizacao()
    if not centro_org:
        return

    if reajuste is None:
        org = getattr(centro_org, "organizacao", None)
        reajuste = getattr(org, "indice_reajuste", Decimal("0")) if org else Decimal("0")

    fator = Decimal("1") + (reajuste or Decimal("0"))

    qs = ContaAssociado.objects.filter(user__is_active=True, user__is_associado=True).select_related("user")
    if ParticipacaoNucleo:
        qs = qs.prefetch_related(
            Prefetch(
                "user__participacoes",
                queryset=ParticipacaoNucleo.objects.select_related("nucleo").filter(status="ativo"),
            )
        )

    lancamentos_payload: list[dict[str, Any]] = []
    carteiras_cache: dict[str, dict[Any, Any]] = {"centro": {}, "conta": {}}
    now = timezone.now()
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    venc_dia = getattr(settings, "MENSALIDADE_VENCIMENTO_DIA", 10)
    data_venc = inicio_mes + timezone.timedelta(days=venc_dia - 1)
    val_assoc = getattr(settings, "MENSALIDADE_ASSOCIACAO", Decimal("50.00")) * fator
    val_assoc = val_assoc.quantize(Decimal("0.01"))
    total = 0
    for conta in qs:
        if not LancamentoFinanceiro.objects.filter(
            centro_custo=centro_org,
            conta_associado=conta,
            tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            data_lancamento=inicio_mes,
        ).exists():
            payload = {
                "centro_custo": centro_org,
                "conta_associado": conta,
                "tipo": LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
                "valor": val_assoc,
                "data_lancamento": inicio_mes,
                "data_vencimento": data_venc,
                "status": LancamentoFinanceiro.Status.PENDENTE,
                "descricao": "Cobrança mensalidade associação",
            }
            atribuir_carteiras_padrao(payload, cache=carteiras_cache)
            lancamentos_payload.append(payload)
        for centro, val_nucleo in _nucleos_do_usuario(conta.user):
            val_nucleo = (val_nucleo * fator).quantize(Decimal("0.01"))
            if not LancamentoFinanceiro.objects.filter(
                centro_custo=centro,
                conta_associado=conta,
                tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO,
                data_lancamento=inicio_mes,
            ).exists():
                payload = {
                    "centro_custo": centro,
                    "conta_associado": conta,
                    "tipo": LancamentoFinanceiro.Tipo.MENSALIDADE_NUCLEO,
                    "valor": val_nucleo,
                    "data_lancamento": inicio_mes,
                    "data_vencimento": data_venc,
                    "status": LancamentoFinanceiro.Status.PENDENTE,
                    "descricao": f"Cobrança mensalidade núcleo {centro.nucleo}",
                }
                atribuir_carteiras_padrao(payload, cache=carteiras_cache)
                lancamentos_payload.append(payload)

    with transaction.atomic():
        for payload in lancamentos_payload:
            lanc = LancamentoFinanceiro.objects.create(**payload)
            total += 1
            conta_destino = lanc.conta_associado_resolvida
            log_financeiro(
                FinanceiroLog.Acao.CRIAR_COBRANCA,
                conta_destino.user if conta_destino else None,
                {},
                {"lancamento": str(lanc.id), "valor": str(lanc.valor)},
            )
            if conta_destino:
                try:
                    enviar_cobranca(conta_destino.user, lanc)
                except Exception as exc:  # pragma: no cover - integração externa
                    logger.error("Falha ao notificar cobrança: %s", exc)
    if total:
        metrics.financeiro_cobrancas_total.inc(total)
