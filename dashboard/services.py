"""Funções auxiliares para agregações do dashboard administrativo."""
from __future__ import annotations

import base64
from collections import OrderedDict
from collections.abc import Mapping
from io import BytesIO
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils.translation import gettext

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


def calculate_events_by_nucleo(organizacao: Any | None) -> OrderedDict[str, int]:
    """Retorna a quantidade de eventos agrupados por núcleo."""

    organizacao_id = _extract_organizacao_id(organizacao)
    totals: OrderedDict[str, int] = OrderedDict()
    if not organizacao_id:
        return totals

    queryset = (
        Evento.objects.filter(organizacao_id=organizacao_id)
        .values("nucleo__nome")
        .annotate(total=Count("id"))
        .order_by("nucleo__nome")
    )

    for item in queryset:
        label = item["nucleo__nome"] or gettext("Sem núcleo")
        totals[label] = item["total"]

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


def _render_empty_chart_message(message: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_alpha(0)
    ax.axis("off")
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=14,
        color="#6b7280",
        wrap=True,
    )
    encoded = _figure_to_data_uri(fig)
    plt.close(fig)
    return encoded


def _figure_to_data_uri(fig: plt.Figure) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight", transparent=True)
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _render_pie_chart(labels: list[str], series: list[int]) -> str:
    total = sum(series)
    if total == 0:
        return _render_empty_chart_message(gettext("Sem dados disponíveis"))

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    colors = _palette_for_length(len(series)) or ["#0ea5e9"]

    def _autopct(pct: float) -> str:
        absolute = int(round(pct * total / 100))
        if absolute == 0:
            return ""
        return f"{pct:.1f}%\n({absolute})"

    wedges, texts, autotexts = ax.pie(
        series,
        labels=labels,
        colors=colors,
        startangle=140,
        autopct=_autopct,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
        textprops={"color": "#111827", "fontsize": 10},
    )

    plt.setp(autotexts, color="#0f172a", fontsize=9, weight="bold")
    ax.axis("equal")
    plt.tight_layout()
    data_uri = _figure_to_data_uri(fig)
    plt.close(fig)
    return data_uri


def _render_bar_chart(labels: list[str], series: list[int]) -> str:
    total = sum(series)
    if total == 0:
        return _render_empty_chart_message(gettext("Sem dados disponíveis"))

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_alpha(0)
    ax.set_facecolor("#ffffff")

    colors = _palette_for_length(len(series)) or ["#2563eb"]
    positions = range(len(labels))
    bars = ax.barh(positions, series, color=colors, edgecolor="none")

    ax.set_yticks(list(positions))
    ax.set_yticklabels(labels, color="#111827", fontsize=10)
    ax.tick_params(axis="x", colors="#374151")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#d1d5db")
    ax.xaxis.grid(True, color="#e5e7eb", linestyle="--", linewidth=0.7)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, series):
        ax.text(
            bar.get_width() + max(total * 0.01, 0.1),
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
            ha="left",
            fontsize=9,
            color="#111827",
        )

    plt.tight_layout()
    data_uri = _figure_to_data_uri(fig)
    plt.close(fig)
    return data_uri


def build_chart_payload(counts: Mapping[str, int], *, chart_type: str = "pie") -> dict[str, Any]:
    """Normaliza contagens em labels, séries, percentuais e gera a imagem do gráfico."""

    labels = list(counts.keys())
    series = [counts[label] for label in labels]
    total = sum(series)
    if total:
        percentages = [round((value / total) * 100, 2) for value in series]
    else:
        percentages = [0 for _ in series]

    if chart_type == "bar":
        image = _render_bar_chart(labels, series)
    else:
        image = _render_pie_chart(labels, series)

    return {
        "labels": labels,
        "series": series,
        "percentages": percentages,
        "total": total,
        "image": image,
        "type": chart_type,
    }
