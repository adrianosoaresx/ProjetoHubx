from __future__ import annotations

from django import template
from django.db.models import Q

from accounts.models import UserType

register = template.Library()


BADGE_STYLES = {
    "nucleado": "--primary:#22c55e; --primary-soft:rgba(34, 197, 94, 0.15); --primary-soft-border:rgba(34, 197, 94, 0.3);",
}


@register.simple_tag(takes_context=True)
def can_request_nucleacao(context, nucleo) -> bool:
    """Return True when the user can request nucleação for the given núcleo.

    The CTA is only available to associados and coordinadores from other núcleos
    who are not already active members or coordinators of the target núcleo.
    """

    request = context.get("request")
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return False

    tipo_usuario = getattr(user, "get_tipo_usuario", None) or getattr(user, "user_type", None)
    if isinstance(tipo_usuario, UserType):
        tipo_usuario = tipo_usuario.value
    allowed_tipos = {
        UserType.ASSOCIADO.value,
        UserType.COORDENADOR.value,
        UserType.NUCLEADO.value,
    }

    if tipo_usuario not in allowed_tipos:
        return False

    if getattr(user, "organizacao_id", None) != getattr(nucleo, "organizacao_id", None):
        return False

    participacoes_manager = getattr(nucleo, "participacoes", None)
    if participacoes_manager is None:
        return False

    active_participacoes = participacoes_manager.filter(user=user).filter(
        Q(status="pendente") | Q(status="ativo", status_suspensao=False)
    )

    return not active_participacoes.exists()


@register.simple_tag(takes_context=True)
def get_nucleacao_status(context, nucleo) -> str | None:
    """Return current participation status for the logged user in the núcleo."""

    request = context.get("request")
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return None

    participacoes_manager = getattr(nucleo, "participacoes", None)
    if participacoes_manager is None:
        return None

    status = (
        participacoes_manager.filter(user=user, deleted=False)
        .values_list("status", flat=True)
        .first()
    )
    return status or None


@register.simple_tag
def badge_style(badge_type: str) -> str:
    """Return visual style tokens for núcleo-related badges."""

    return BADGE_STYLES.get(str(badge_type or "").lower(), "")
