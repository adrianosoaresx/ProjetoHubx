from __future__ import annotations

from django import template
from django.utils.translation import gettext as _

from accounts.models import UserType

register = template.Library()


BADGE_STYLES = {
    "associado": "--primary:#6366f1; --primary-soft:rgba(99, 102, 241, 0.15); --primary-soft-border:rgba(99, 102, 241, 0.3);",
    "nucleado": "--primary:#22c55e; --primary-soft:rgba(34, 197, 94, 0.15); --primary-soft-border:rgba(34, 197, 94, 0.3);",
    "coordenador": "--primary:#f97316; --primary-soft:rgba(249, 115, 22, 0.15); --primary-soft-border:rgba(249, 115, 22, 0.3);",
    "consultor": "--primary:#8b5cf6; --primary-soft:rgba(139, 92, 246, 0.15); --primary-soft-border:rgba(139, 92, 246, 0.3);",
}


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
            badges.append({"label": label, "style": BADGE_STYLES["coordenador"], "type": "coordenador"})
            types_present.add("coordenador")
        else:
            if nucleo_nome:
                label = _("Nucleado · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Nucleado")
            badges.append({"label": label, "style": BADGE_STYLES["nucleado"], "type": "nucleado"})
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
        badges.append({"label": label, "style": BADGE_STYLES["consultor"], "type": "consultor"})
        types_present.add("consultor")

    if getattr(user, "nucleo", None) and not {"coordenador", "nucleado"} & types_present:
        nucleo_nome = getattr(user.nucleo, "nome", "")
        if getattr(user, "is_coordenador", False):
            if nucleo_nome:
                label = _("Coordenador · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Coordenador")
            badges.append({"label": label, "style": BADGE_STYLES["coordenador"], "type": "coordenador"})
            types_present.add("coordenador")
        else:
            if nucleo_nome:
                label = _("Nucleado · %(nucleo)s") % {"nucleo": nucleo_nome}
            else:
                label = _("Nucleado")
            badges.append({"label": label, "style": BADGE_STYLES["nucleado"], "type": "nucleado"})
            types_present.add("nucleado")

    if getattr(user, "user_type", "") == UserType.CONSULTOR.value and "consultor" not in types_present:
        badges.append({"label": _("Consultor"), "style": BADGE_STYLES["consultor"], "type": "consultor"})
        types_present.add("consultor")

    if getattr(user, "is_associado", False) and not types_present:
        badges.append({"label": _("Associado"), "style": BADGE_STYLES["associado"], "type": "associado"})
        types_present.add("associado")
    elif getattr(user, "is_associado", False) and "associado" not in types_present and not badges:
        badges.append({"label": _("Associado"), "style": BADGE_STYLES["associado"], "type": "associado"})
        types_present.add("associado")

    if getattr(user, "user_type", "") == UserType.ASSOCIADO.value and "associado" not in types_present and not badges:
        badges.append({"label": _("Associado"), "style": BADGE_STYLES["associado"], "type": "associado"})

    return [{"label": badge["label"], "style": badge.get("style", "")} for badge in badges]
