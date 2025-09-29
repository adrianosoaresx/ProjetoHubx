"""Serviços relacionados a tokens e convites."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Tuple

from django.contrib.auth import get_user_model

from .models import TokenAcesso
from .utils import _send_webhook

User = get_user_model()


def invite_created(token: TokenAcesso, codigo: str) -> None:
    """Notifica criação de um convite."""
    _send_webhook({"event": "invite.created", "id": str(token.id), "code": codigo})


def invite_used(token: TokenAcesso) -> None:
    """Notifica utilização de um convite."""
    _send_webhook({"event": "invite.used", "id": str(token.id)})


def invite_revoked(token: TokenAcesso) -> None:
    """Notifica revogação de um convite."""
    _send_webhook({"event": "invite.revoked", "id": str(token.id)})


def create_invite_token(
    *,
    gerado_por: User,
    tipo_destino: str,
    data_expiracao: datetime | None = None,
    organizacao=None,
) -> Tuple[TokenAcesso, str]:
    """Cria um ``TokenAcesso`` com código secreto e retorna (token, codigo)."""

    try:
        target_role = TokenAcesso.TipoUsuario(tipo_destino)
    except ValueError as exc:  # pragma: no cover - validação defensiva
        raise ValueError("Tipo de token inválido") from exc

    if target_role != TokenAcesso.TipoUsuario.CONVIDADO:
        raise ValueError("Somente tokens para convidados podem ser gerados.")

    codigo = TokenAcesso.generate_code()
    codigo_preview = TokenAcesso.build_codigo_preview(codigo)
    token = TokenAcesso(
        gerado_por=gerado_por,
        tipo_destino=target_role.value,
        data_expiracao=data_expiracao,
        organizacao=organizacao,
        codigo_preview=codigo_preview,
    )
    token.set_codigo(codigo)
    token.save()
    return token, codigo


def find_token_by_code(codigo: str) -> TokenAcesso:
    """Retorna o ``TokenAcesso`` correspondente ao ``codigo``.

    A busca é realizada apenas por meio do hash SHA-256, sem iteração
    adicional sobre tokens legados com ``codigo_salt``.
    """
    codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
    return TokenAcesso.objects.get(codigo_hash=codigo_hash)
