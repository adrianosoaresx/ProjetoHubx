from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from django.utils import timezone

from dashboard.services import (
    build_chart_payload,
    build_time_series_chart,
    calculate_event_status_totals,
    calculate_membership_totals,
    calculate_monthly_membros,
)
from eventos.models import Evento
from nucleos.models import Nucleo
from organizacoes.models import Organizacao
from services import nucleos_metrics


def _serialize_datetime(value: datetime | None) -> str | None:
    """Normaliza datas para ``isoformat`` serializável."""

    if not value:
        return None
    if timezone.is_naive(value):
        return value.isoformat()
    return timezone.localtime(value).isoformat()


def get_membership_totals(organizacao_id: str) -> dict[str, Any]:
    """Retorna totais de membros por tipo e payload de gráfico para a organização informada."""

    totals = calculate_membership_totals(organizacao_id)
    return {
        "organizacao_id": organizacao_id,
        "totals": dict(totals),
        "chart": build_chart_payload(totals),
    }


def get_event_status_totals(organizacao_id: str) -> dict[str, Any]:
    """Retorna totais de eventos por status e payload de gráfico para a organização informada."""

    totals = calculate_event_status_totals(organizacao_id)
    return {
        "organizacao_id": organizacao_id,
        "totals": dict(totals),
        "chart": build_chart_payload(totals),
    }


def get_monthly_members(organizacao_id: str, *, months: int = 12, reference: datetime | None = None) -> dict[str, Any]:
    """Retorna evolução mensal de novos membros com figura Plotly serializável para a organização."""

    data_points = calculate_monthly_membros(
        organizacao_id,
        months=months,
        reference=reference,
    )
    chart = build_time_series_chart(
        data_points,
        value_field="total",
        std_field="std_dev",
        label="Novos associados",
        yaxis_title="Total",
    )
    serialized_data = [
        {**point, "period": _serialize_datetime(point.get("period"))}
        for point in data_points
    ]
    return {
        "organizacao_id": organizacao_id,
        "months": months,
        "data": serialized_data,
        "chart": chart,
    }


def get_nucleo_metrics(organizacao_id: str, nucleo_id: str) -> dict[str, Any]:
    """Retorna métricas consolidadas de um núcleo específico limitado à organização informada."""

    nucleo = (
        Nucleo.objects.filter(organizacao_id=organizacao_id, id=nucleo_id, deleted=False)
        .values("id", "nome", "organizacao_id")
        .first()
    )
    if not nucleo:
        return {
            "organizacao_id": organizacao_id,
            "nucleo_id": nucleo_id,
            "error": "Núcleo não encontrado para a organização.",
        }

    return {
        "organizacao_id": organizacao_id,
        "nucleo": nucleo,
        "total_membros": nucleos_metrics.get_total_membros(nucleo_id),
        "total_suplentes": nucleos_metrics.get_total_suplentes(nucleo_id),
        "membros_por_status": nucleos_metrics.get_membros_por_status(nucleo_id),
        "taxa_participacao": nucleos_metrics.get_taxa_participacao(organizacao_id),
    }


def get_organizacao_description(organizacao_id: str) -> dict[str, Any]:
    """Retorna descrição e metadados básicos da organização para uso em contexto de RAG."""

    organizacao = (
        Organizacao.objects.filter(id=organizacao_id, deleted=False)
        .values("id", "nome", "descricao", "tipo", "cidade", "estado", "site")
        .first()
    )
    return organizacao or {"organizacao_id": organizacao_id, "error": "Organização não encontrada."}


def get_organizacao_nucleos_context(organizacao_id: str) -> dict[str, Any]:
    """Retorna lista de núcleos ativos da organização com dados relevantes para contexto RAG."""

    nucleos = list(
        Nucleo.objects.filter(organizacao_id=organizacao_id, ativo=True, deleted=False)
        .values("id", "nome", "descricao", "classificacao")
        .order_by("nome")
    )
    return {"organizacao_id": organizacao_id, "nucleos": nucleos}


def get_future_events_context(
    organizacao_id: str,
    *,
    limit: int | None = 10,
    from_date: datetime | None = None,
    nucleo_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Retorna eventos futuros da organização filtrados para composição de contexto RAG."""

    reference = from_date or timezone.now()
    queryset = Evento.objects.filter(
        organizacao_id=organizacao_id,
        data_inicio__gte=reference,
        deleted=False,
    ).values(
        "id",
        "titulo",
        "descricao",
        "data_inicio",
        "data_fim",
        "local_nome",
        "nucleo_id",
    )

    if nucleo_ids:
        queryset = queryset.filter(nucleo_id__in=list(nucleo_ids))

    events = list(queryset.order_by("data_inicio"))
    if limit is not None:
        events = events[:limit]

    return {
        "organizacao_id": organizacao_id,
        "from_date": _serialize_datetime(reference),
        "events": [
            {
                **event,
                "data_inicio": _serialize_datetime(event.get("data_inicio")),
                "data_fim": _serialize_datetime(event.get("data_fim")),
            }
            for event in events
        ],
    }
