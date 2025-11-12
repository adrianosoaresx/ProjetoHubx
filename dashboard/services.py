"""Funções auxiliares para agregações do dashboard administrativo."""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from collections.abc import Mapping
from datetime import datetime, date
from decimal import Decimal
from statistics import StatisticsError, pstdev
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils import timezone
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


def _normalize_reference(reference: datetime | None = None) -> datetime:
    """Normaliza a data de referência para o timezone configurado."""

    normalized = reference or timezone.now()
    if timezone.is_naive(normalized):
        normalized = timezone.make_aware(normalized)
    return normalized


def _month_start(moment: datetime) -> datetime:
    """Retorna o primeiro instante do mês da data informada."""

    normalized = _normalize_reference(moment)
    return normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _shift_month(moment: datetime, offset: int) -> datetime:
    """Desloca ``moment`` para o primeiro dia do mês conforme ``offset``."""

    base = _month_start(moment)
    month_index = base.month - 1 + offset
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    return base.replace(year=year, month=month)


def _generate_month_periods(
    count: int, *, reference: datetime | None = None
) -> list[datetime]:
    """Gera ``count`` meses em ordem cronológica até ``reference`` (inclusive)."""

    if count <= 0:
        return []

    anchor = _month_start(reference or timezone.now())
    periods: list[datetime] = []
    current = anchor
    for _ in range(count):
        periods.append(current)
        current = _shift_month(current, -1)
    return list(reversed(periods))


def _baseline_for_periods(
    periods: list[datetime], *, include_std: bool = False
) -> OrderedDict[date, dict[str, Any]]:
    """Inicializa um ``OrderedDict`` com registros vazios para os períodos."""

    baseline: OrderedDict[date, dict[str, Any]] = OrderedDict()
    for period in periods:
        record: dict[str, Any] = {"period": period, "total": 0}
        if include_std:
            record["std_dev"] = 0.0
        baseline[_period_key(period)] = record
    return baseline


def _period_key(period: datetime) -> datetime.date:
    """Normaliza um ``datetime`` para a data correspondente."""

    normalized = _normalize_reference(period)
    return normalized.date()


def _calculate_std_dev(values: list[float]) -> float:
    """Calcula o desvio padrão populacional com proteção para listas vazias."""

    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return 0.0
    if len(filtered) == 1:
        return 0.0
    try:
        return round(float(pstdev(filtered)), 2)
    except StatisticsError:  # pragma: no cover - salvaguarda
        return 0.0


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


def calculate_monthly_associates(
    organizacao: Any | None,
    *,
    months: int = 12,
    reference: datetime | None = None,
) -> list[dict[str, Any]]:
    """Retorna evolução mensal de novos associados com desvio padrão diário."""

    periods = _generate_month_periods(months, reference=reference)
    baseline = _baseline_for_periods(periods, include_std=True)

    organizacao_id = _extract_organizacao_id(organizacao)
    if not organizacao_id or not periods:
        return list(baseline.values())

    start = periods[0]
    associados_qs = User.objects.filter(
        organizacao_id=organizacao_id,
        is_associado=True,
        date_joined__isnull=False,
        date_joined__gte=start,
    )

    daily_counts = (
        associados_qs.annotate(day=TruncDay("date_joined"))
        .values("day")
        .annotate(total=Count("id"))
    )

    for item in daily_counts:
        day = item.get("day")
        if not day:
            continue
        month_start = _month_start(day)
        record = baseline.get(_period_key(month_start))
        if not record:
            continue
        total = int(item.get("total") or 0)
        record["total"] += total
        record.setdefault("_daily_totals", []).append(total)

    for record in baseline.values():
        daily = record.pop("_daily_totals", [])
        record["std_dev"] = _calculate_std_dev(daily)

    return list(baseline.values())


def calculate_monthly_nucleados(
    organizacao: Any | None,
    *,
    months: int = 12,
    reference: datetime | None = None,
) -> list[dict[str, Any]]:
    """Retorna evolução mensal de nucleados ativos com desvio padrão diário."""

    periods = _generate_month_periods(months, reference=reference)
    baseline = _baseline_for_periods(periods, include_std=True)

    organizacao_id = _extract_organizacao_id(organizacao)
    if not organizacao_id or not periods:
        return list(baseline.values())

    start = periods[0]
    participacoes_qs = ParticipacaoNucleo.objects.filter(
        nucleo__organizacao_id=organizacao_id,
        status="ativo",
        created_at__gte=start,
    )

    daily_counts = (
        participacoes_qs.annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(total=Count("id"))
    )

    for item in daily_counts:
        day = item.get("day")
        if not day:
            continue
        month_start = _month_start(day)
        record = baseline.get(_period_key(month_start))
        if not record:
            continue
        total = int(item.get("total") or 0)
        record["total"] += total
        record.setdefault("_daily_totals", []).append(total)

    for record in baseline.values():
        daily = record.pop("_daily_totals", [])
        record["std_dev"] = _calculate_std_dev(daily)

    return list(baseline.values())


def calculate_monthly_event_registrations(
    organizacao: Any | None,
    *,
    months: int = 12,
    reference: datetime | None = None,
) -> list[dict[str, Any]]:
    """Retorna a contagem mensal de inscrições confirmadas."""

    periods = _generate_month_periods(months, reference=reference)
    baseline = _baseline_for_periods(periods, include_std=False)

    organizacao_id = _extract_organizacao_id(organizacao)
    if not organizacao_id or not periods:
        return list(baseline.values())

    start = periods[0]
    inscricoes_qs = InscricaoEvento.objects.filter(
        evento__organizacao_id=organizacao_id,
        status="confirmada",
        data_confirmacao__isnull=False,
        data_confirmacao__gte=start,
    )

    daily_counts = (
        inscricoes_qs.annotate(day=TruncDay("data_confirmacao"))
        .values("day")
        .annotate(total=Count("id"))
    )

    for item in daily_counts:
        day = item.get("day")
        if not day:
            continue
        month_start = _month_start(day)
        record = baseline.get(_period_key(month_start))
        if not record:
            continue
        record["total"] += int(item.get("total") or 0)

    return list(baseline.values())


def calculate_monthly_registration_values(
    organizacao: Any | None,
    *,
    months: int = 12,
    reference: datetime | None = None,
) -> list[dict[str, Any]]:
    """Retorna a soma mensal dos valores pagos com desvio padrão."""

    periods = _generate_month_periods(months, reference=reference)
    baseline = _baseline_for_periods(periods, include_std=True)

    organizacao_id = _extract_organizacao_id(organizacao)
    if not organizacao_id or not periods:
        return list(baseline.values())

    start = periods[0]
    inscricoes_qs = InscricaoEvento.objects.filter(
        evento__organizacao_id=organizacao_id,
        status="confirmada",
        valor_pago__isnull=False,
        data_confirmacao__isnull=False,
        data_confirmacao__gte=start,
    ).values("data_confirmacao", "valor_pago")

    grouped_values: dict[date, list[float]] = defaultdict(list)
    totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))

    for item in inscricoes_qs:
        confirmation = item.get("data_confirmacao")
        value = item.get("valor_pago")
        if not confirmation or value is None:
            continue
        month_start = _period_key(_month_start(confirmation))
        if month_start not in baseline:
            continue
        totals[month_start] += Decimal(value)
        grouped_values[month_start].append(float(value))

    for key, record in baseline.items():
        record["total"] = float(totals.get(key, Decimal("0")))
        record["std_dev"] = _calculate_std_dev(grouped_values.get(key, []))

    return list(baseline.values())


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


def build_time_series_chart(
    data_points: list[dict[str, Any]],
    *,
    value_field: str,
    label: str,
    std_field: str | None = None,
    color: str = "#2563eb",
    value_format: str = ".0f",
    value_prefix: str = "",
    value_suffix: str = "",
    yaxis_title: str = "",
    yaxis_tickprefix: str = "",
    yaxis_ticksuffix: str = "",
) -> dict[str, Any]:
    """Gera figura Plotly de série temporal com opção de banda de desvio padrão."""

    if not data_points:
        empty = _empty_figure(gettext("Sem dados disponíveis"))
        return {"points": [], "figure": empty.to_dict(), "type": "line"}

    x_values = [point["period"] for point in data_points]
    y_values = [float(point.get(value_field) or 0.0) for point in data_points]

    if not any(y_values):
        figure = _empty_figure(gettext("Sem dados disponíveis"))
    else:
        figure = go.Figure()
        std_values: list[float] = []
        if std_field:
            std_values = [float(point.get(std_field) or 0.0) for point in data_points]

        band_color = _adjust_color_luminance(color, 0.4)
        band_border = _adjust_color_luminance(color, 0.2)

        if std_field and any(std_values):
            upper = [value + std for value, std in zip(y_values, std_values)]
            lower = [max(0.0, value - std) for value, std in zip(y_values, std_values)]

            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=upper,
                    mode="lines",
                    line={"width": 0, "color": band_border},
                    hoverinfo="skip",
                    showlegend=False,
                    name="upper",
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=lower,
                    mode="lines",
                    line={"width": 0, "color": band_border},
                    fill="tonexty",
                    fillcolor=band_color,
                    name=gettext("Desvio padrão"),
                    customdata=[[std] for std in std_values],
                    hovertemplate=(
                        "<b>%{x|%b %Y}</b><br>"
                        + gettext("Desvio padrão")
                        + ": "
                        + value_prefix
                        + "%{customdata[0]:"
                        + value_format
                        + "}"
                        + value_suffix
                        + "<extra></extra>"
                    ),
                )
            )

        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                name=label,
                line={"color": color, "width": 3},
                marker={
                    "size": 8,
                    "color": _adjust_color_luminance(color, -0.02),
                    "line": {"color": "#ffffff", "width": 1},
                },
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>"
                    + label
                    + ": "
                    + value_prefix
                    + "%{y:"
                    + value_format
                    + "}"
                    + value_suffix
                    + "<extra></extra>"
                ),
            )
        )

        figure.update_layout(
            _base_layout(
                xaxis={
                    "title": "",
                    "tickformat": "%b %Y",
                    "dtick": "M1",
                    "hoverformat": "%b %Y",
                },
                yaxis={
                    "title": yaxis_title,
                    "tickprefix": yaxis_tickprefix,
                    "ticksuffix": yaxis_ticksuffix,
                    "rangemode": "tozero",
                },
                hovermode="x unified",
                margin={"l": 72, "r": 32, "t": 48, "b": 96},
                height=420,
            )
        )

    serialized_points: list[dict[str, Any]] = []
    for point in data_points:
        serialized = dict(point)
        period = serialized.get("period")
        if hasattr(period, "isoformat"):
            serialized["period"] = period.isoformat()
        serialized_points.append(serialized)

    return {"points": serialized_points, "figure": figure.to_dict(), "type": "line"}


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

    tooltip_labels: list[str] = []
    for original_label, legend_label in zip(labels, legend_labels):
        sanitized = _strip_numeric_suffix(legend_label)
        if sanitized == legend_label:
            sanitized = original_label
        tooltip_labels.append(sanitized)

    customdata = [
        [tooltip_label, value]
        for tooltip_label, value in zip(tooltip_labels, series)
    ]

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
