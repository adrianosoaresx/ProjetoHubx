"""Funções auxiliares para agregações do dashboard administrativo."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from typing import Any

from django.contrib.auth import get_user_model

from eventos.models import Evento, InscricaoEvento
from nucleos.models import ParticipacaoNucleo

User = get_user_model()


def _extract_organizacao_id(organizacao: Any | None) -> Any | None:
    """Retorna o identificador da organização ou ``None`` se indisponível."""

    if not organizacao:
        return None
    return getattr(organizacao, "id", organizacao)


def calculate_membership_totals(organizacao: Any | None) -> OrderedDict[str, int]:
    """Calcula totais de associados e nucleados para a organização."""

    organizacao_id = _extract_organizacao_id(organizacao)
    totals = OrderedDict((label, 0) for label in ("Associados", "Nucleados"))
    if not organizacao_id:
        return totals

    totals["Associados"] = User.objects.filter(
        organizacao_id=organizacao_id,
        is_associado=True,
    ).count()
    totals["Nucleados"] = ParticipacaoNucleo.objects.filter(
        status="ativo",
        nucleo__organizacao_id=organizacao_id,
    ).count()
    return totals


def calculate_event_status_totals(organizacao: Any | None) -> OrderedDict[str, int]:
    """Retorna a distribuição de eventos por status para a organização."""

    organizacao_id = _extract_organizacao_id(organizacao)
    totals: OrderedDict[str, int] = OrderedDict(
        (status.label, 0) for status in Evento.Status
    )
    if not organizacao_id:
        return totals

    queryset = Evento.objects.filter(organizacao_id=organizacao_id)
    for status in Evento.Status:
        totals[status.label] = queryset.filter(status=status).count()
    return totals


def count_confirmed_event_registrations(organizacao: Any | None) -> int:
    """Conta inscrições confirmadas para eventos da organização."""

    organizacao_id = _extract_organizacao_id(organizacao)
    if not organizacao_id:
        return 0
    return InscricaoEvento.objects.filter(
        evento__organizacao_id=organizacao_id,
        status="confirmada",
    ).count()


def build_chart_payload(counts: Mapping[str, int]) -> dict[str, Any]:
    """Normaliza contagens em labels, séries e percentuais."""

    labels = list(counts.keys())
    series = [counts[label] for label in labels]
    total = sum(series)
    if total:
        percentages = [round((value / total) * 100, 2) for value in series]
    else:
        percentages = [0 for _ in series]

    return {
        "labels": labels,
        "series": series,
        "percentages": percentages,
        "total": total,
    }
