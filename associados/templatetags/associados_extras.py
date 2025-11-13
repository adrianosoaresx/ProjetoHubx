from __future__ import annotations

import re

from django import template
from django.utils.translation import gettext as _

from accounts.models import UserType

register = template.Library()


BADGE_STYLES = {
    "associado": "--primary:#6366f1; --primary-soft:rgba(99, 102, 241, 0.15); --primary-soft-border:rgba(99, 102, 241, 0.3);",
    "nucleado": "--primary:#22c55e; --primary-soft:rgba(34, 197, 94, 0.15); --primary-soft-border:rgba(34, 197, 94, 0.3);",
    "coordenador": "--primary:#f97316; --primary-soft:rgba(249, 115, 22, 0.15); --primary-soft-border:rgba(249, 115, 22, 0.3);",
    "consultor": "--primary:#8b5cf6; --primary-soft:rgba(139, 92, 246, 0.15); --primary-soft-border:rgba(139, 92, 246, 0.3);",
    "admin": "--primary:#ef4444; --primary-soft:rgba(239, 68, 68, 0.15); --primary-soft-border:rgba(239, 68, 68, 0.3);",
    "operador": "--primary:#0ea5e9; --primary-soft:rgba(14, 165, 233, 0.15); --primary-soft-border:rgba(14, 165, 233, 0.3);",
    "convidado": "--primary:#9ca3af; --primary-soft:rgba(156, 163, 175, 0.15); --primary-soft-border:rgba(156, 163, 175, 0.3);",
    "root": "--primary:#facc15; --primary-soft:rgba(250, 204, 21, 0.15); --primary-soft-border:rgba(250, 204, 21, 0.3);",
}


BADGE_ICONS = {
    "associado": "id-card",
    "nucleado": "users",
    "coordenador": "flag",
    "consultor": "briefcase",
    "admin": "shield-check",
    "operador": "settings-2",
    "convidado": "user",
    "root": "crown",
}

DEFAULT_BADGE_ICON = "badge-check"


def _make_badge(label: str, badge_type: str) -> dict[str, str]:
    style = BADGE_STYLES.get(badge_type, "")
    icon = BADGE_ICONS.get(badge_type, DEFAULT_BADGE_ICON)
    return {"label": label, "style": style, "icon": icon, "type": badge_type}


def _get_prefetched(manager, cache_key):
    related_cache = getattr(manager, "instance", None)
    if related_cache is not None:
        cache = getattr(related_cache, "_prefetched_objects_cache", {})
        if cache_key in cache:
            return cache[cache_key]
    return None


@register.simple_tag
def usuario_badges(user):
    """Retorna metadados de etiquetas para o usuário."""

    badges: list[dict[str, str]] = []
    types_present: set[str] = set()

    participacoes_manager = getattr(user, "participacoes", None)
    participacoes = []
    if participacoes_manager is not None:
        prefetched = _get_prefetched(participacoes_manager, "participacoes")
        if prefetched is not None:
            participacoes = list(prefetched)
        else:
            participacoes = list(
                participacoes_manager.select_related("nucleo").all()
            )

    for participacao in participacoes:
        if participacao.status != "ativo" or getattr(participacao, "status_suspensao", False):
            continue
        nucleo = getattr(participacao, "nucleo", None)
        nucleo_nome = getattr(nucleo, "nome", "")

        if participacao.papel == "coordenador":
            papel = participacao.get_papel_coordenador_display() if participacao.papel_coordenador else ""
            if papel:
                if nucleo_nome:
                    label = _("%(papel)s · %(nucleo)s") % {
                        "papel": papel,
                        "nucleo": nucleo_nome,
                    }
                else:
                    label = papel
            elif nucleo_nome:
                label = _("Coordenador · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Coordenador")
            badges.append(_make_badge(label, "coordenador"))
            types_present.add("coordenador")
        else:
            if nucleo_nome:
                label = _("Nucleado · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Nucleado")
            badges.append(_make_badge(label, "nucleado"))
            types_present.add("nucleado")

    nucleos_consultoria_manager = getattr(user, "nucleos_consultoria", None)
    consultoria = []
    if nucleos_consultoria_manager is not None:
        prefetched = _get_prefetched(nucleos_consultoria_manager, "nucleos_consultoria")
        if prefetched is not None:
            consultoria = list(prefetched)
        else:
            consultoria = list(nucleos_consultoria_manager.all())

    for nucleo in consultoria:
        nucleo_nome = getattr(nucleo, "nome", "")
        if nucleo_nome:
            label = _("Consultor · %(nucleo)s") % {"nucleo": nucleo_nome}
        else:
            label = _("Consultor")
        badges.append(_make_badge(label, "consultor"))
        types_present.add("consultor")

    if getattr(user, "nucleo", None) and not {"coordenador", "nucleado"} & types_present:
        nucleo_nome = getattr(user.nucleo, "nome", "")
        if getattr(user, "is_coordenador", False):
            if nucleo_nome:
                label = _("Coordenador · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Coordenador")
            badges.append(_make_badge(label, "coordenador"))
            types_present.add("coordenador")
        else:
            if nucleo_nome:
                label = _("Nucleado · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Nucleado")
            badges.append(_make_badge(label, "nucleado"))
            types_present.add("nucleado")

    if getattr(user, "user_type", "") == UserType.CONSULTOR.value and "consultor" not in types_present:
        badges.append(_make_badge(_("Consultor"), "consultor"))
        types_present.add("consultor")

    if getattr(user, "is_associado", False) and not types_present:
        badges.append(_make_badge(_("Associado"), "associado"))
        types_present.add("associado")
    elif getattr(user, "is_associado", False) and "associado" not in types_present and not badges:
        badges.append(_make_badge(_("Associado"), "associado"))
        types_present.add("associado")

    if getattr(user, "user_type", "") == UserType.ASSOCIADO.value and "associado" not in types_present and not badges:
        badges.append(_make_badge(_("Associado"), "associado"))

    if getattr(user, "user_type", "") == UserType.ADMIN.value:
        badges = [badge for badge in badges if badge.get("type") != "nucleado"]

    return [
        {
            "label": badge["label"],
            "style": badge.get("style", ""),
            "icon": badge.get("icon", DEFAULT_BADGE_ICON),
            "type": badge.get("type", ""),
        }
        for badge in badges
    ]


@register.simple_tag
def usuario_tipo_badge(user):
    """Retorna os metadados da etiqueta do tipo principal do usuário."""

    tipo_attr = getattr(user, "get_tipo_usuario", "")
    tipo = tipo_attr() if callable(tipo_attr) else tipo_attr
    if not tipo:
        tipo = getattr(user, "user_type", "") or ""
    if not tipo:
        return None

    try:
        label = UserType(tipo).label
    except ValueError:
        label = str(tipo).title()

    badge_type = tipo if tipo in BADGE_STYLES else "associado"
    badge = _make_badge(label, badge_type)
    badge["type"] = tipo
    return badge


@register.simple_tag
def usuario_tipo_label(user) -> str:
    """Retorna o rótulo legível da tipificação do usuário."""

    tipo = getattr(user, "get_tipo_usuario", "") or ""
    if not tipo:
        return ""
    try:
        return UserType(tipo).label
    except ValueError:
        return str(tipo)


@register.filter
def digits_only(value: str | None) -> str:
    """Remove todos os caracteres que não sejam dígitos."""

    if not value:
        return ""
    return re.sub(r"\D+", "", str(value))
