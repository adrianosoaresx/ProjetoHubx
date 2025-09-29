from __future__ import annotations

"""Políticas de permissão para emissão de convites."""

from accounts.models import UserType
from tokens.models import TokenAcesso


def can_issue_invite(issuer, target_role: str) -> bool:
    """Retorna True se *issuer* puder emitir convite para *target_role* (RF-05)."""

    issuer_type = getattr(issuer, "user_type", None)
    try:
        role = TokenAcesso.TipoUsuario(target_role)
    except ValueError:
        return False

    if role != TokenAcesso.TipoUsuario.CONVIDADO:
        return False

    return issuer_type in {
        UserType.ROOT,
        UserType.ADMIN,
        UserType.COORDENADOR,
    }
