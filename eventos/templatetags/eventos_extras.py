from __future__ import annotations

from django import template
from django.utils.translation import gettext as _

register = template.Library()

PUBLIC_BADGE_STYLE = "--primary:#2563eb; --primary-soft:rgba(37, 99, 235, 0.15); --primary-soft-border:rgba(37, 99, 235, 0.3);"
NUCLEO_BADGE_STYLE = "--primary:#0ea5e9; --primary-soft:rgba(14, 165, 233, 0.15); --primary-soft-border:rgba(14, 165, 233, 0.3);"
TARGET_BADGE_MAP = {
    1: {
        "label": _("Somente nucleados"),
        "style": "--primary:#22c55e; --primary-soft:rgba(34, 197, 94, 0.15); --primary-soft-border:rgba(34, 197, 94, 0.3);",
    },
    2: {
        "label": _("Apenas associados"),
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
    else:
        cover_label = getattr(nucleo, "nome", "") or _("Núcleo não definido")
        cover_style = NUCLEO_BADGE_STYLE
        target_badge = TARGET_BADGE_MAP.get(publico_alvo)

    cover_badges = []
    if cover_label:
        cover_badges.append({"label": cover_label, "style": cover_style})

    return {
        "cover_badges": cover_badges,
        "target_badge": target_badge,
    }
