from __future__ import annotations

from django.db.models import Q

from accounts.models import UserType

from .models import Evento


def filter_eventos_por_usuario(qs, user, *, evento_field: str | None = None):
    """Restringe um queryset de eventos conforme o perfil do usuário.

    Args:
        qs: Queryset de :class:`Evento` ou relacionado a evento (via ``evento_field``).
        user: Usuário autenticado que realizará a consulta.
        evento_field: Nome do campo relacionado ao evento quando ``qs`` não é
            diretamente de :class:`Evento`.
    """

    if not getattr(user, "is_authenticated", False):
        return qs.none()

    if getattr(user, "user_type", None) == UserType.ROOT.value:
        return qs

    prefix = f"{evento_field}__" if evento_field else ""

    organizacao_field = f"{prefix}organizacao"
    qs = qs.filter(**{organizacao_field: getattr(user, "organizacao", None)})

    tipo_usuario = getattr(user, "get_tipo_usuario", None)
    if isinstance(tipo_usuario, UserType):  # pragma: no cover - defensive fallback
        tipo_usuario = tipo_usuario.value
    nucleos_qs = getattr(user, "nucleos", None)
    nucleo_ids = list(nucleos_qs.values_list("id", flat=True)) if nucleos_qs is not None else []

    if tipo_usuario in {UserType.ADMIN.value, UserType.OPERADOR.value}:
        return qs

    if tipo_usuario == UserType.ASSOCIADO.value and not nucleo_ids:
        status_field = f"{prefix}status"
        publico_field = f"{prefix}publico_alvo"
        return qs.filter(**{status_field: Evento.Status.ATIVO}).filter(**{publico_field: 0})

    if tipo_usuario in {UserType.NUCLEADO.value, UserType.COORDENADOR.value} or nucleo_ids:
        publico_field = f"{prefix}publico_alvo"
        nucleo_field = f"{prefix}nucleo__in"
        filtro = Q(**{publico_field: 0})
        if nucleo_ids:
            filtro |= Q(**{nucleo_field: nucleo_ids})
        return qs.filter(filtro).distinct()

    return qs
