from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from ..models import CentroCusto, ContaAssociado, LancamentoFinanceiro

try:
    from nucleos.models import ParticipacaoNucleo
except Exception:  # pragma: no cover - núcleo opcional
    ParticipacaoNucleo = None  # type: ignore


def _centro_organizacao() -> CentroCusto | None:
    """Retorna o centro de custo principal da organização."""
    return CentroCusto.objects.filter(tipo=CentroCusto.Tipo.ORGANIZACAO).order_by("created_at").first()


def _nucleos_do_usuario(user) -> Iterable[CentroCusto]:
    """Obtém centros de custo dos núcleos ativos do usuário."""
    if not ParticipacaoNucleo:
        return []
    participacoes = getattr(user, "participacoes", None)
    if participacoes is None:
        return []
    ativos = [p.nucleo for p in participacoes.all() if p.status == "aprovado"]
    centros: list[CentroCusto] = []
    for nucleo in ativos:
        centro = nucleo.centros_custo.filter(tipo=CentroCusto.Tipo.NUCLEO).order_by("created_at").first()
        if centro:
            centros.append(centro)
    return centros


def gerar_cobrancas() -> None:
    """Cria lançamentos de cobrança para associados e núcleos."""
    centro_org = _centro_organizacao()
    if not centro_org:
        return

    qs = ContaAssociado.objects.filter(user__is_active=True).select_related("user")
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
    val_nucleo = getattr(settings, "MENSALIDADE_NUCLEO", Decimal("30.00"))

    for conta in qs:
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
        for centro in _nucleos_do_usuario(conta.user):
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
        if lancamentos:
            LancamentoFinanceiro.objects.bulk_create(lancamentos)
            for lanc in lancamentos:
                _enviar_notificacao_cobranca(lanc.conta_associado.user, lanc)


def _enviar_notificacao_cobranca(user, lancamento) -> None:  # pragma: no cover
    """Placeholder para integração com sistema de notificações."""
    pass
