"""Funções auxiliares para agregações do dashboard administrativo."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils.translation import gettext
from plotly import graph_objects as go

from eventos.models import Evento, InscricaoEvento
from nucleos.models import ParticipacaoNucleo

User = get_user_model()


ASSOCIADOS_NUCLEADOS_LABEL = gettext("Associados nucleados")
ASSOCIADOS_NAO_NUCLEADOS_LABEL = gettext("Associados não nucleados")
EVENTOS_PUBLICOS_LABEL = gettext("Eventos públicos")
SEM_NUCLEO_LABEL = gettext("Sem núcleo")


def _extract_organizacao_id(organizacao: Any | None) -> Any | None:
    """Retorna o identificador da organização ou ``None`` se indisponível."""

    if not organizacao:
        return None
    return getattr(organizacao, "id", organizacao)


def calculate_membership_totals(organizacao: Any | None) -> OrderedDict[str, int]:
    """Calcula totais de associados nucleados e não nucleados."""

    organizacao_id = _extract_organizacao_id(organizacao)
    totals = OrderedDict(
        (label, 0)
        for label in (ASSOCIADOS_NUCLEADOS_LABEL, ASSOCIADOS_NAO_NUCLEADOS_LABEL)
    )
    if not organizacao_id:
        return totals

    associados_qs = User.objects.filter(
        organizacao_id=organizacao_id,
        is_associado=True,
    )
    total_associados = associados_qs.count()

    total_nucleados = (
        ParticipacaoNucleo.objects.filter(
            status="ativo",
            nucleo__organizacao_id=organizacao_id,
            user__organizacao_id=organizacao_id,
        )
        .values("user_id")
        .distinct()
        .count()
    )
    total_nao_nucleados = max(total_associados - total_nucleados, 0)

    totals[ASSOCIADOS_NUCLEADOS_LABEL] = total_nucleados
    totals[ASSOCIADOS_NAO_NUCLEADOS_LABEL] = total_nao_nucleados
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


def calculate_events_by_nucleo(organizacao: Any | None) -> OrderedDict[str, int]:
    """Retorna a quantidade de eventos agrupados por núcleo."""

    organizacao_id = _extract_organizacao_id(organizacao)
    totals: OrderedDict[str, int] = OrderedDict()
    if not organizacao_id:
        return totals

    queryset = (
        Evento.objects.filter(organizacao_id=organizacao_id)
        .values("nucleo__nome", "publico_alvo")
        .annotate(total=Count("id"))
        .order_by("nucleo__nome", "publico_alvo")
    )

    public_total = 0
    for item in queryset:
        if item["publico_alvo"] == 0 and not item["nucleo__nome"]:
            public_total += item["total"]
            continue

        label = item["nucleo__nome"] or SEM_NUCLEO_LABEL
        if label not in totals:
            totals[label] = 0
        totals[label] += item["total"]

    if public_total:
        totals[EVENTOS_PUBLICOS_LABEL] = public_total

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


CHART_PALETTE = [
    "#0ea5e9",  # sky-500
    "#2563eb",  # blue-600
    "#7c3aed",  # violet-600
    "#22c55e",  # green-500
    "#f97316",  # orange-500
    "#eab308",  # yellow-500
    "#ec4899",  # pink-500
]


def _palette_for_length(length: int) -> list[str]:
    if length <= 0:
        return []
    repeats = (length // len(CHART_PALETTE)) + 1
    return (CHART_PALETTE * repeats)[:length]


def _base_layout(**extras: Any) -> dict[str, Any]:
    layout: dict[str, Any] = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(255,255,255,1)",
        "margin": {"l": 40, "r": 40, "t": 50, "b": 40},
        "font": {"color": "#0f172a"},
        "legend": {
            "bgcolor": "rgba(255,255,255,0.95)",
            "bordercolor": "rgba(209,213,219,0.6)",
            "borderwidth": 1,
            "font": {"size": 12},
        },
    }
    layout.update(extras)
    return layout


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        _base_layout(
            annotations=[
                {
                    "text": message,
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 16, "color": "#6b7280"},
                }
            ],
            xaxis={"visible": False},
            yaxis={"visible": False},
            height=400,
        )
    )
    return fig


def _pie_chart(labels: list[str], series: list[int]) -> go.Figure:
    total = sum(series)
    if total == 0:
        return _empty_figure(gettext("Sem dados disponíveis"))

    colors = _palette_for_length(len(series)) or ["#0ea5e9"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=series,
                hole=0.35,
                marker={
                    "colors": colors,
                    "line": {"color": "#ffffff", "width": 2},
                },
                hovertemplate="<b>%{label}</b><br>Valor: %{value}<br>%{percent}<extra></extra>",
                textinfo="label+value",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        _base_layout(
            legend={
                "orientation": "v",
                "yanchor": "middle",
                "xanchor": "left",
                "x": 1.05,
                "y": 0.5,
                "bgcolor": "rgba(255,255,255,0.95)",
                "bordercolor": "rgba(209,213,219,0.6)",
                "borderwidth": 1,
                "font": {"size": 12},
            },
            margin={"l": 20, "r": 140, "t": 50, "b": 30},
            height=420,
        )
    )
    return fig


def _bar_chart(labels: list[str], series: list[int]) -> go.Figure:
    total = sum(series)
    if total == 0:
        return _empty_figure(gettext("Sem dados disponíveis"))

    colors = _palette_for_length(len(series)) or ["#2563eb"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=series,
                y=labels,
                orientation="h",
                marker={
                    "color": colors,
                    "line": {"color": "#e5e7eb", "width": 1},
                },
                text=[str(value) for value in series],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Valor: %{x}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        _base_layout(
            xaxis={
                "title": "",
                "gridcolor": "#e5e7eb",
                "zerolinecolor": "#d1d5db",
                "tickfont": {"size": 12, "color": "#374151"},
            },
            yaxis={
                "title": "",
                "tickfont": {"size": 12, "color": "#0f172a"},
                "categoryorder": "total ascending",
            },
            bargap=0.25,
            margin={"l": 140, "r": 40, "t": 50, "b": 40},
            height=420,
        )
    )
    return fig


def build_chart_payload(counts: Mapping[str, int], *, chart_type: str = "pie") -> dict[str, Any]:
    """Normaliza contagens e gera os metadados e figura Plotly correspondente."""

    labels = list(counts.keys())
    series = [counts[label] for label in labels]
    total = sum(series)
    if total:
        percentages = [round((value / total) * 100, 2) for value in series]
    else:
        percentages = [0 for _ in series]

    if chart_type == "bar":
        figure = _bar_chart(labels, series)
    else:
        figure = _pie_chart(labels, series)

    return {
        "labels": labels,
        "series": series,
        "percentages": percentages,
        "total": total,
        "figure": figure.to_dict(),
        "type": chart_type,
    }
