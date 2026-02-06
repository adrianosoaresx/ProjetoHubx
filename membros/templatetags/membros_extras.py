from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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
    "nucleus": "--primary:#06b6d4; --primary-soft:rgba(6, 182, 212, 0.15); --primary-soft-border:rgba(6, 182, 212, 0.3);",
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
    "nucleus": "building-2",
}

DEFAULT_BADGE_ICON = "badge-check"


def _make_badge(label: str, badge_type: str) -> dict[str, str]:
    style = BADGE_STYLES.get(badge_type, "")
    icon = BADGE_ICONS.get(badge_type, DEFAULT_BADGE_ICON)
    return {"label": label, "style": style, "icon": icon, "type": badge_type}


def _active_participacoes_data(user) -> list[dict[str, object]]:
    participacoes_manager = getattr(user, "participacoes", None)
    participacoes = []
    if participacoes_manager is not None:
        prefetched = _get_prefetched(participacoes_manager, "participacoes")
        if prefetched is not None:
            participacoes = list(prefetched)
        else:
            participacoes = list(participacoes_manager.select_related("nucleo").all())

    participacoes_data: list[dict[str, object]] = []
    for participacao in participacoes:
        if participacao.status != "ativo" or getattr(participacao, "status_suspensao", False):
            continue

        nucleo = getattr(participacao, "nucleo", None)
        papel_coordenador = participacao.get_papel_coordenador_display() if participacao.papel_coordenador else ""
        promotion_label = papel_coordenador if participacao.papel == "coordenador" else _("Nucleado")

        participacoes_data.append(
            {
                "promotion_label": promotion_label,
                "nucleo_nome": getattr(nucleo, "nome", ""),
                "nucleo_id": getattr(nucleo, "id", None),
                "is_coordenador": participacao.papel == "coordenador",
                "papel_coordenador": papel_coordenador,
            }
        )

    return participacoes_data


def _get_prefetched(manager, cache_key):
    related_cache = getattr(manager, "instance", None)
    if related_cache is not None:
        cache = getattr(related_cache, "_prefetched_objects_cache", {})
        if cache_key in cache:
            return cache[cache_key]
    return None


@register.simple_tag
def rating_stars(average) -> list[str]:
    """Return star states for a five-star rating with half-star rounding."""

    try:
        value = Decimal(str(average))
    except (InvalidOperation, TypeError, ValueError):
        value = Decimal("0")

    half_steps = (value * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    rounded = half_steps / 2
    clamped = min(max(rounded, Decimal("0")), Decimal("5"))

    stars: list[str] = []
    half_step = Decimal("0.5")

    for position in range(1, 6):
        full_threshold = Decimal(position)
        half_threshold = full_threshold - half_step

        if clamped >= full_threshold:
            stars.append("full")
        elif clamped >= half_threshold:
            stars.append("half")
        else:
            stars.append("empty")

    return stars


def _has_nucleo_specific_badge(user, tipo: str) -> bool:
    if tipo == UserType.COORDENADOR.value:
        participacoes_manager = getattr(user, "participacoes", None)
        participacoes = []
        if participacoes_manager is not None:
            prefetched = _get_prefetched(participacoes_manager, "participacoes")
            if prefetched is not None:
                participacoes = list(prefetched)
            else:
                participacoes = list(participacoes_manager.select_related("nucleo").all())

        for participacao in participacoes:
            if participacao.status != "ativo" or getattr(participacao, "status_suspensao", False):
                continue
            if participacao.papel == "coordenador" and getattr(participacao, "nucleo", None):
                return True

        if getattr(user, "is_coordenador", False) and getattr(user, "nucleo", None):
            return True

    if tipo == UserType.NUCLEADO.value:
        participacoes_manager = getattr(user, "participacoes", None)
        participacoes = []
        if participacoes_manager is not None:
            prefetched = _get_prefetched(participacoes_manager, "participacoes")
            if prefetched is not None:
                participacoes = list(prefetched)
            else:
                participacoes = list(participacoes_manager.select_related("nucleo").all())

        for participacao in participacoes:
            if participacao.status != "ativo" or getattr(participacao, "status_suspensao", False):
                continue
            if participacao.papel != "coordenador" and getattr(participacao, "nucleo", None):
                return True

        if getattr(user, "nucleo", None):
            return True

    if tipo == UserType.CONSULTOR.value:
        nucleos_consultoria_manager = getattr(user, "nucleos_consultoria", None)
        consultoria = []
        if nucleos_consultoria_manager is not None:
            prefetched = _get_prefetched(nucleos_consultoria_manager, "nucleos_consultoria")
            if prefetched is not None:
                consultoria = list(prefetched)
            else:
                consultoria = list(nucleos_consultoria_manager.all())

        return any(nucleo is not None for nucleo in consultoria)

    return False


@register.simple_tag
def usuario_badges(user):
    """Retorna metadados de etiquetas para o usuário."""

    badges: list[dict[str, str]] = []
    types_present: set[str] = set()
    seen_promotion_labels: set[str] = set()

    active_participacoes = _active_participacoes_data(user)
    seen_nucleus: set[int | str] = set()

    for participacao in active_participacoes:
        promotion_label = str(participacao.get("promotion_label") or "")
        is_coordenador = bool(participacao.get("is_coordenador"))
        nucleo_nome = str(participacao.get("nucleo_nome") or "")
        nucleo_id = participacao.get("nucleo_id")

        if is_coordenador:
            label = promotion_label or _("Coordenador")
            badge = _make_badge(label, "coordenador")
            types_present.add("coordenador")
            should_add_promotion_badge = True
        else:
            label = promotion_label or _("Nucleado")
            badge = _make_badge(label, "nucleado")
            types_present.add("nucleado")
            should_add_promotion_badge = label not in seen_promotion_labels

        seen_promotion_labels.add(label)

        if should_add_promotion_badge:
            badge["group"] = "promotion"
            badges.append(badge)

        if nucleo_nome:
            nucleus_key = nucleo_id if nucleo_id is not None else nucleo_nome
            if nucleus_key in seen_nucleus:
                continue
            seen_nucleus.add(nucleus_key)
            nucleus_badge = _make_badge(nucleo_nome, "nucleus")
            nucleus_badge["group"] = "nucleus"
            badges.append(nucleus_badge)
            types_present.add("nucleus")

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
            promotion_badge = _make_badge(_("Coordenador"), "coordenador")
            promotion_badge["group"] = "promotion"
            badges.append(promotion_badge)
            types_present.add("coordenador")
        else:
            promotion_badge = _make_badge(_("Nucleado"), "nucleado")
            promotion_badge["group"] = "promotion"
            badges.append(promotion_badge)
            types_present.add("nucleado")

        if nucleo_nome:
            nucleus_badge = _make_badge(nucleo_nome, "nucleus")
            nucleus_badge["group"] = "nucleus"
            badges.append(nucleus_badge)
            types_present.add("nucleus")

    if getattr(user, "user_type", "") == UserType.CONSULTOR.value and "consultor" not in types_present:
        badges.append(_make_badge(_("Consultor"), "consultor"))
        types_present.add("consultor")

    associado_flag = getattr(user, "is_associado", False) or getattr(user, "user_type", "") == UserType.ASSOCIADO.value
    has_associado_badge = "associado" in types_present or any(
        badge.get("type") == "associado" for badge in badges
    )
    if associado_flag and not badges and not has_associado_badge:
        badges.append(_make_badge(_("Associado"), "associado"))
        types_present.add("associado")

    if getattr(user, "user_type", "") == UserType.ADMIN.value:
        badges = [badge for badge in badges if badge.get("type") != "nucleado"]

    return [
        {
            "label": badge["label"],
            "style": badge.get("style", ""),
            "icon": badge.get("icon", DEFAULT_BADGE_ICON),
            "type": badge.get("type", ""),
            "group": badge.get("group", ""),
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

    if tipo in {
        UserType.COORDENADOR.value,
        UserType.CONSULTOR.value,
        UserType.NUCLEADO.value,
    }:
        if _has_nucleo_specific_badge(user, tipo):
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
