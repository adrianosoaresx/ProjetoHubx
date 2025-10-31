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
import matplotlib.patheffects as patheffects
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Patch
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils.translation import gettext

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


VALUE_FONT_SIZE = 12
LABEL_FONT_SIZE = 12
AXIS_FONT_SIZE = 11
EMPTY_STATE_FONT_SIZE = 16
ANNOTATION_BOX_STYLE = {
    "boxstyle": "round,pad=0.35",
    "facecolor": "#ffffff",
    "edgecolor": "none",
    "alpha": 0.85,
}


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
        fontsize=EMPTY_STATE_FONT_SIZE,
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

    fig = plt.figure(figsize=(6, 4))
    fig.patch.set_facecolor("#ffffff")
    fig.patch.set_alpha(1)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#ffffff")

    colors = _palette_for_length(len(series)) or ["#0ea5e9"]
    radius = 1.0
    height = 0.3
    start_angle = 0.0
    outline_effect = patheffects.withStroke(linewidth=2, foreground="#f3f4f6")
    legend_handles: list[Patch] = []

    for label, value, color in zip(labels, series, colors):
        if value == 0:
            start_angle += 360 * (value / max(total, 1))
            continue

        angle = (value / total) * 360
        theta = np.linspace(np.deg2rad(start_angle), np.deg2rad(start_angle + angle), 40)
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)

        top_face = [(0.0, 0.0, height)] + list(zip(x, y, np.full_like(x, height)))
        bottom_face = [(0.0, 0.0, 0.0)] + list(zip(x, y, np.zeros_like(x)))

        for face in (top_face, bottom_face):
            poly = Poly3DCollection([face], facecolors=color, edgecolors="#ffffff", linewidths=0.5)
            poly.set_alpha(0.95)
            ax.add_collection3d(poly)

        for i in range(len(theta) - 1):
            side_vertices = [
                (x[i], y[i], 0.0),
                (x[i + 1], y[i + 1], 0.0),
                (x[i + 1], y[i + 1], height),
                (x[i], y[i], height),
            ]
            side = Poly3DCollection([side_vertices], facecolors=color, edgecolors="#ffffff", linewidths=0.3)
            side.set_alpha(0.95)
            ax.add_collection3d(side)

        radial_start = [
            (0.0, 0.0, 0.0),
            (x[0], y[0], 0.0),
            (x[0], y[0], height),
            (0.0, 0.0, height),
        ]
        radial_end = [
            (0.0, 0.0, 0.0),
            (x[-1], y[-1], 0.0),
            (x[-1], y[-1], height),
            (0.0, 0.0, height),
        ]
        for radial_face in (radial_start, radial_end):
            radial_poly = Poly3DCollection([radial_face], facecolors=color, edgecolors="#ffffff", linewidths=0.3)
            radial_poly.set_alpha(0.95)
            ax.add_collection3d(radial_poly)

        handle = Patch(
            facecolor=color,
            edgecolor="#1f2937",
            label=f"{label} ({value})",
            linewidth=0.5,
        )
        handle.set_path_effects([outline_effect])
        legend_handles.append(handle)

        start_angle += angle

    ax.view_init(elev=25, azim=135)
    ax.set_box_aspect((1, 1, 0.35))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_zlim(0, height * 2.2)
    ax.set_axis_off()
    if legend_handles:
        ax.legend(
            handles=legend_handles,
            loc="center left",
            bbox_to_anchor=(1.05, 0.5),
            fontsize=LABEL_FONT_SIZE,
            frameon=False,
        )

    fig.subplots_adjust(left=0.0, right=0.75, top=0.95, bottom=0.05)
    data_uri = _figure_to_data_uri(fig)
    plt.close(fig)
    return data_uri


def _render_bar_chart(labels: list[str], series: list[int]) -> str:
    total = sum(series)
    if total == 0:
        return _render_empty_chart_message(gettext("Sem dados disponíveis"))

    fig = plt.figure(figsize=(6, 4))
    fig.patch.set_facecolor("#ffffff")
    fig.patch.set_alpha(1)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#ffffff")

    colors = _palette_for_length(len(series)) or ["#2563eb"]
    values = np.array(series, dtype=float)
    y_positions = np.arange(len(labels))
    bar_depth = 0.6
    bar_height = 0.4
    outline_effect = patheffects.withStroke(linewidth=2, foreground="#f3f4f6")

    ax.bar3d(
        np.zeros(len(series)),
        y_positions - bar_depth / 2,
        np.zeros(len(series)),
        values,
        np.full(len(series), bar_depth),
        np.full(len(series), bar_height),
        color=colors,
        shade=True,
        edgecolor="#f3f4f6",
        linewidth=0.5,
    )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(
        labels,
        color="#111827",
        fontsize=LABEL_FONT_SIZE,
        fontweight="bold",
    )
    ax.set_ylabel("")
    max_value = float(values.max()) if len(values) else 1.0
    xmax = max_value if max_value > 0 else 1.0
    ax.set_xlim(0, xmax * 1.1)
    ax.set_xticks(np.linspace(0, xmax, num=4))
    ax.set_xlabel("")
    ax.set_zticks([])
    ax.view_init(elev=20, azim=-60)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))
        axis.pane.set_edgecolor((1.0, 1.0, 1.0, 0.0))
    ax.tick_params(axis="x", colors="#374151", labelsize=AXIS_FONT_SIZE)
    ax.tick_params(axis="y", colors="#111827", labelsize=LABEL_FONT_SIZE)

    legend_handles = []
    for label, value, color in zip(labels, values, colors):
        if value == 0:
            continue
        handle = Patch(
            facecolor=color,
            edgecolor="#1f2937",
            linewidth=0.5,
            label=f"{label} ({int(value)})",
        )
        handle.set_path_effects([outline_effect])
        legend_handles.append(handle)

    if legend_handles:
        ax.legend(
            handles=legend_handles,
            loc="center left",
            bbox_to_anchor=(1.05, 0.5),
            fontsize=LABEL_FONT_SIZE,
            frameon=False,
        )

    fig.subplots_adjust(left=0.08, right=0.78, top=0.95, bottom=0.1)
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
