from __future__ import annotations

"""Políticas de permissão para emissão de convites."""

from accounts.models import UserType
from tokens.models import TokenAcesso


def can_issue_invite(issuer, target_role: str) -> bool:
    """Retorna True se *issuer* puder emitir convite para *target_role* (RF-05)."""

    issuer_type = getattr(issuer, "user_type", None)
    if issuer_type == UserType.ROOT:
        return target_role == TokenAcesso.TipoUsuario.ADMIN
    if issuer_type == UserType.ADMIN:
        return target_role in {
            TokenAcesso.TipoUsuario.COORDENADOR,
            TokenAcesso.TipoUsuario.NUCLEADO,
            TokenAcesso.TipoUsuario.ASSOCIADO,
            TokenAcesso.TipoUsuario.CONVIDADO,
        }
    if issuer_type == UserType.COORDENADOR:
        return target_role == TokenAcesso.TipoUsuario.CONVIDADO
    return False
