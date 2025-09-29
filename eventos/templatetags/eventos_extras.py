from __future__ import annotations
from django import template
from django.utils.translation import gettext as _

from eventos.models import Evento

register = template.Library()

PUBLIC_BADGE_STYLE = "--primary:#2563eb; --primary-soft:rgba(37, 99, 235, 0.15); --primary-soft-border:rgba(37, 99, 235, 0.3);"
NUCLEO_BADGE_STYLE = "--primary:#0ea5e9; --primary-soft:rgba(14, 165, 233, 0.15); --primary-soft-border:rgba(14, 165, 233, 0.3);"
STATUS_BADGE_STYLE_MAP = {
    Evento.Status.ATIVO: "--primary:#16a34a; --primary-soft:rgba(22, 163, 74, 0.15); --primary-soft-border:rgba(22, 163, 74, 0.3);",
    Evento.Status.CONCLUIDO: "--primary:#2563eb; --primary-soft:rgba(37, 99, 235, 0.15); --primary-soft-border:rgba(37, 99, 235, 0.3);",
    Evento.Status.CANCELADO: "--primary:#dc2626; --primary-soft:rgba(220, 38, 38, 0.15); --primary-soft-border:rgba(220, 38, 38, 0.3);",
    Evento.Status.PLANEJAMENTO: "--primary:#f97316; --primary-soft:rgba(249, 115, 22, 0.15); --primary-soft-border:rgba(249, 115, 22, 0.3);",
}
TARGET_BADGE_MAP = {
    1: {
        "label": _("Somente nucleados"),
        "style": "--primary:#22c55e; --primary-soft:rgba(34, 197, 94, 0.15); --primary-soft-border:rgba(34, 197, 94, 0.3);",
    },
    2: {
        "label": _("Associados"),
        "style": "--primary:#6366f1; --primary-soft:rgba(99, 102, 241, 0.15); --primary-soft-border:rgba(99, 102, 241, 0.3);",
    },
}


@register.simple_tag
def evento_badges(evento):
    """Retorna dados de etiquetas para o card de evento."""

    publico_alvo = getattr(evento, "publico_alvo", None)
    nucleo = getattr(evento, "nucleo", None)

    if publico_alvo == 0:
        cover_label = _("Público")
        cover_style = PUBLIC_BADGE_STYLE
        target_badge = None
    elif publico_alvo == 1:
        cover_label = getattr(nucleo, "nome", "") or _("Núcleo não definido")
        cover_style = NUCLEO_BADGE_STYLE
        target_badge = TARGET_BADGE_MAP.get(publico_alvo)
    else:
        cover_label = getattr(nucleo, "nome", "")
        cover_style = NUCLEO_BADGE_STYLE
        target_badge = TARGET_BADGE_MAP.get(publico_alvo)

    cover_badges = []
    if cover_label:
        cover_badges.append({"label": cover_label, "style": cover_style})

    status_label = ""
    get_status_display = getattr(evento, "get_status_display", None)
    if callable(get_status_display):
        status_label = get_status_display()

    if status_label:
        cover_badges.append(
            {
                "label": status_label,
                "style": STATUS_BADGE_STYLE_MAP.get(
                    getattr(evento, "status", None), PUBLIC_BADGE_STYLE
                ),
            }
        )

    return {
        "cover_badges": cover_badges,
        "target_badge": target_badge,
    }
