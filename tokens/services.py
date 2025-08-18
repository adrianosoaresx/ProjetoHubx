from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Iterable

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ApiToken

User = get_user_model()


def generate_token(
    user: User | None,
    client_name: str | None,
    scope: str,
    expires_in: timedelta | None,
) -> str:
    """Gera um token de API e retorna o valor bruto."""

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = timezone.now() + expires_in if expires_in else None
    ApiToken.objects.create(
        user=user,
        client_name=client_name or "",
        token_hash=token_hash,
        scope=scope,
        expires_at=expires_at,
    )
    return raw_token


def revoke_token(token_id: uuid.UUID) -> None:
    token = ApiToken.objects.get(id=token_id, revoked_at__isnull=True)
    now = timezone.now()
    token.revoked_at = now
    token.deleted = True
    token.deleted_at = now
    token.save(update_fields=["revoked_at", "deleted", "deleted_at"])


def list_tokens(user: User) -> Iterable[ApiToken]:
    qs = ApiToken.objects.all()
    if not user.is_superuser:
        qs = qs.filter(user=user)
    return qs

from datetime import datetime
from typing import Tuple

from .models import TokenAcesso


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
    """Retorna o ``TokenAcesso`` correspondente ao ``codigo`` ou levanta ``DoesNotExist``."""

    for token in TokenAcesso.objects.all():
        if token.check_codigo(codigo):
            return token
    raise TokenAcesso.DoesNotExist
