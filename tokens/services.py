"""Serviços relacionados a tokens e convites."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Iterable, Tuple

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ApiToken, ApiTokenLog, TokenAcesso
from .utils import _send_webhook, revoke_token, rotate_token

User = get_user_model()


def token_created(token: ApiToken, raw: str) -> None:
    """Dispara webhook para notificar criação de ``token``."""
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    _send_webhook({"event": "created", "id": str(token.id), "token": token_hash})


def invite_created(token: TokenAcesso, codigo: str) -> None:
    """Notifica criação de um convite."""
    _send_webhook({"event": "invite.created", "id": str(token.id), "code": codigo})


def invite_used(token: TokenAcesso) -> None:
    """Notifica utilização de um convite."""
    _send_webhook({"event": "invite.used", "id": str(token.id)})


def invite_revoked(token: TokenAcesso) -> None:
    """Notifica revogação de um convite."""
    _send_webhook({"event": "invite.revoked", "id": str(token.id)})


def generate_token(
    user: User | None,
    client_name: str | None,
    scope: str,
    expires_in: timedelta | None = None,
    device_fingerprint: str | None = None,
) -> str:
    """Gera um token de API e retorna o valor bruto."""

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = timezone.now() + expires_in if expires_in else None
    token = ApiToken.objects.create(
        user=user,
        client_name=client_name or "",
        token_hash=token_hash,
        device_fingerprint=device_fingerprint,
        scope=scope,
        expires_at=expires_at,
    )

    token_created(token, raw_token)

    return raw_token


def list_tokens(user: User) -> Iterable[ApiToken]:
    qs = ApiToken.objects.all()
    if not user.is_superuser:
        qs = qs.filter(user=user)
    return qs


def create_invite_token(
    *,
    gerado_por: User,
    tipo_destino: str,
    data_expiracao: datetime | None = None,
    organizacao=None,
    nucleos=None,
) -> Tuple[TokenAcesso, str]:
    """Cria um ``TokenAcesso`` com código secreto e retorna (token, codigo)."""

    codigo = TokenAcesso.generate_code()
    token = TokenAcesso(
        gerado_por=gerado_por,
        tipo_destino=tipo_destino,
        data_expiracao=data_expiracao,
        organizacao=organizacao,
    )
    token.set_codigo(codigo)
    token.save()
    if nucleos:
        token.nucleos.set(nucleos)
    return token, codigo


def find_token_by_code(codigo: str) -> TokenAcesso:
    """Retorna o ``TokenAcesso`` correspondente ao ``codigo``.

    A busca é realizada apenas por meio do hash SHA-256, sem iteração
    adicional sobre tokens legados com ``codigo_salt``.
    """
    codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
    return TokenAcesso.objects.get(codigo_hash=codigo_hash)
