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
    token.revoked_at = timezone.now()
    token.save(update_fields=["revoked_at"])


def list_tokens(user: User) -> Iterable[ApiToken]:
    qs = ApiToken.objects.all()
    if not user.is_superuser:
        qs = qs.filter(user=user)
    return qs
