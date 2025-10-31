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


def _clamp(value: float, minimum: float = 0.0, maximum: float = 255.0) -> float:
    """Limita ``value`` dentro do intervalo informado."""

    return max(minimum, min(value, maximum))


def _adjust_color_luminance(color: str, factor: float) -> str:
    """Ajusta a luminosidade de uma cor hexadecimal.

    ``factor`` deve estar entre ``-1`` (mais escuro) e ``1`` (mais claro).
    """

    hex_color = color.strip().lstrip("#")
    if len(hex_color) not in (3, 6):
        return color

    if len(hex_color) == 3:
        hex_color = "".join(component * 2 for component in hex_color)

    try:
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)
    except ValueError:
        return color

    if factor >= 0:
        red = _clamp(red + (255 - red) * factor)
        green = _clamp(green + (255 - green) * factor)
        blue = _clamp(blue + (255 - blue) * factor)
    else:
        red = _clamp(red * (1 + factor))
        green = _clamp(green * (1 + factor))
        blue = _clamp(blue * (1 + factor))

    return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"


def _palette_for_length(length: int) -> list[str]:
    if length <= 0:
        return []
    repeats = (length // len(CHART_PALETTE)) + 1
    return (CHART_PALETTE * repeats)[:length]


def _base_layout(**extras: Any) -> dict[str, Any]:
    layout: dict[str, Any] = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 40, "r": 40, "t": 48, "b": 96},
        "font": {"color": "var(--text-primary, #0f172a)"},
        "legend": {
            "orientation": "h",
            "yanchor": "top",
            "xanchor": "center",
            "x": 0.5,
            "y": -0.18,
            "bgcolor": "rgba(255,255,255,0.0)",
            "bordercolor": "rgba(148,163,184,0.4)",
            "borderwidth": 1,
            "font": {"size": 12},
            "itemwidth": 80,
        },
        "hoverlabel": {
            "bgcolor": "rgba(255,255,255,0.95)",
            "bordercolor": "rgba(148,163,184,0.4)",
            "font": {"color": "var(--text-primary, #0f172a)"},
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
                    "font": {"size": 16, "color": "var(--text-secondary, #6b7280)"},
                }
            ],
            xaxis={"visible": False},
            yaxis={"visible": False},
            height=400,
        )
    )
    return fig


def _format_legend_label(label: str, total: int) -> str:
    template = gettext("%(label)s · %(total)s")
    return template % {"label": label, "total": total}


def _is_numeric_suffix(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    normalized = normalized.replace(".", "").replace(",", "")
    return normalized.isdigit()


def _strip_numeric_suffix(label: str) -> str:
    trimmed = label.strip()
    separators = (" · ", "·", ",", " - ", " – ", " — ")
    for separator in separators:
        if separator in trimmed:
            head, _, tail = trimmed.partition(separator)
            if _is_numeric_suffix(tail):
                return head.strip()
    return trimmed


def _pie_chart(labels: list[str], series: list[int]) -> go.Figure:
    total = sum(series)
    if total == 0:
        return _empty_figure(gettext("Sem dados disponíveis"))

    colors = _palette_for_length(len(series)) or ["#0ea5e9"]
    highlight_colors = [_adjust_color_luminance(color, 0.08) for color in colors]
    shadow_colors = [_adjust_color_luminance(color, -0.15) for color in colors]
    legend_labels = [
        _format_legend_label(label, value) for label, value in zip(labels, series)
    ]
    tooltip_labels = [_strip_numeric_suffix(label) for label in legend_labels]
    customdata = [[tooltip_label, value] for tooltip_label, value in zip(tooltip_labels, series)]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=legend_labels,
                values=series,
                hole=0.45,
                marker={
                    "colors": shadow_colors,
                    "line": {"color": "rgba(15,23,42,0.25)", "width": 1},
                },
                hoverinfo="skip",
                textinfo="none",
                showlegend=False,
                sort=False,
                direction="clockwise",
                rotation=2,
                opacity=0.55,
                pull=0.015,
            ),
            go.Pie(
                labels=legend_labels,
                values=series,
                customdata=customdata,
                hole=0.55,
                marker={
                    "colors": highlight_colors,
                    "line": {"color": "#ffffff", "width": 2},
                },
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Total: %{value}<br>"
                    "Participação: %{percent}<extra></extra>"
                ),
                textinfo="none",
                sort=False,
            ),
        ]
    )
    fig.update_layout(
        _base_layout(
            legend={
                "traceorder": "normal",
            },
            margin={"l": 32, "r": 32, "t": 48, "b": 120},
            height=440,
            annotations=[
                {
                    "text": gettext("Total") + f"<br><b>{total}</b>",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 18, "color": "var(--text-primary, #0f172a)"},
                }
            ],
        )
    )
    return fig


def _bar_chart(labels: list[str], series: list[int]) -> go.Figure:
    total = sum(series)
    if total == 0:
        return _empty_figure(gettext("Sem dados disponíveis"))

    colors = _palette_for_length(len(series)) or ["#2563eb"]
    legend_labels = [
        _format_legend_label(label, value) for label, value in zip(labels, series)
    ]

    traces: list[go.Bar] = []
    for index, (label, value, legend_label, color) in enumerate(
        zip(labels, series, legend_labels, colors)
    ):
        traces.append(
            go.Bar(
                x=[label],
                y=[value],
                marker={
                    "color": color,
                    "line": {"color": "#e5e7eb", "width": 1},
                },
                customdata=[[label, value]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Total: %{customdata[1]}<extra></extra>"
                ),
                name=legend_label,
                showlegend=True,
                legendgroup=str(index),
            )
        )

    fig = go.Figure(data=traces)
    fig.update_layout(
        _base_layout(
            xaxis={
                "title": "",
                "gridcolor": "#e5e7eb",
                "zerolinecolor": "#cbd5f5",

                "showticklabels": False,
                "showgrid": False,
                "ticks": "",

                "automargin": True,
            },
            yaxis={
                "title": "",
                "tickfont": {"size": 12, "color": "var(--text-secondary, #374151)"},
                "gridcolor": "#e5e7eb",
                "rangemode": "tozero",
            },
            legend={
                "traceorder": "normal",
            },
            bargap=0.35,
            margin={"l": 48, "r": 24, "t": 48, "b": 140},
            barmode="group",
            height=440,
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
