from __future__ import annotations

from typing import Optional

from accounts.models import UserType
from nucleos.models import Nucleo


def _has_active_participation(user, nucleo: Optional[Nucleo]) -> bool:
    participacoes = getattr(user, "participacoes", None)
    if participacoes is None:
        return False
    query = participacoes.filter(status="ativo", status_suspensao=False)
    if nucleo is not None:
        query = query.filter(nucleo=nucleo)
    return query.exists()


def _is_consultor(user, nucleo: Optional[Nucleo]) -> bool:
    if nucleo is not None:
        consultor_id = getattr(nucleo, "consultor_id", None)
        if consultor_id and consultor_id == getattr(user, "id", None):
            return True
    nucleos_consultoria = getattr(user, "nucleos_consultoria", None)
    if nucleos_consultoria is not None:
        try:
            qs = nucleos_consultoria.filter(deleted=False)
            if nucleo is not None:
                qs = qs.filter(pk=getattr(nucleo, "pk", None))
            return qs.exists()
        except Exception:  # pragma: no cover - defensive
            return False
    return False


def can_manage_feed(user, nucleo: Optional[Nucleo] = None) -> bool:
    """Centraliza a regra de permissão para publicar/visualizar em núcleos.

    Admins e operadores podem publicar mesmo sem participação formal desde que
    estejam atuando dentro da própria organização. Nucleados, coordenadores e
    consultores precisam estar vinculados ao núcleo (participação ativa ou
    designação direta como consultor).
    """

    if not user or not getattr(user, "is_authenticated", False):
        return False

    user_type = getattr(user, "user_type", None)
    if user_type == UserType.ROOT:
        return True

    if user_type in {UserType.ADMIN, UserType.OPERADOR}:
        if nucleo is None:
            return True
        organizacao_id = getattr(user, "organizacao_id", None)
        return bool(organizacao_id) and organizacao_id == getattr(nucleo, "organizacao_id", None)

    if nucleo is None:
        return _has_active_participation(user, None) or _is_consultor(user, None)

    return _has_active_participation(user, nucleo) or _is_consultor(user, nucleo)
