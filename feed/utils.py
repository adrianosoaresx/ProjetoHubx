from __future__ import annotations

from django.db.models import QuerySet

from accounts.models import UserType
from nucleos.models import Nucleo


def get_allowed_nucleos_for_user(user) -> QuerySet[Nucleo]:
    """Retorna os núcleos em que o usuário pode publicar."""

    if not user or not getattr(user, "is_authenticated", False):
        return Nucleo.objects.none()

    if getattr(user, "user_type", None) in {UserType.ROOT, UserType.ADMIN, UserType.OPERADOR}:
        if user.user_type == UserType.ROOT:
            return Nucleo.objects.all()
        organizacao_id = getattr(user, "organizacao_id", None)
        if organizacao_id:
            return Nucleo.objects.filter(organizacao_id=organizacao_id)
        return Nucleo.objects.none()

    nucleo_ids: set[int] = set()

    participacoes = getattr(user, "participacoes", None)
    if participacoes is not None:
        nucleo_ids.update(
            participacoes.filter(status="ativo", status_suspensao=False).values_list("nucleo_id", flat=True)
        )

    nucleo_id = getattr(user, "nucleo_id", None)
    if nucleo_id:
        nucleo_ids.add(nucleo_id)

    nucleos_consultoria = getattr(user, "nucleos_consultoria", None)
    if nucleos_consultoria is not None:
        nucleo_ids.update(nucleos_consultoria.filter(deleted=False).values_list("id", flat=True))

    return Nucleo.objects.filter(id__in=nucleo_ids)
