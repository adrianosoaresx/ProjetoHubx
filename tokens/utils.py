from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils import timezone

from .models import ApiToken, ApiTokenLog

User = get_user_model()


def get_client_ip(request: HttpRequest) -> str:
    """Return the client's IP address.

    Prefers the ``X-Forwarded-For`` header, falling back to ``REMOTE_ADDR``.
    When multiple IPs are present in ``X-Forwarded-For``, the first one is
    assumed to be the client IP.
    """

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _send_webhook(payload: dict[str, object]) -> None:
    """Queue task to send ``payload`` to the configured webhook."""

    url = getattr(settings, "TOKENS_WEBHOOK_URL", None)
    if not url:
        return

    # Imported lazily to avoid circular import with tasks module
    from .tasks import send_webhook

    send_webhook.delay(payload)


def revoke_token(
    token_id: uuid.UUID,
    revogado_por: User | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    usuario_log: User | None = None,
) -> bool:
    """Revoga o token indicado e dispara webhook."""

    token = ApiToken.all_objects.get(id=token_id)
    if token.revoked_at:
        return False

    now = timezone.now()
    token.revoked_at = now
    token.revogado_por = revogado_por or token.user
    token.deleted = True
    token.deleted_at = now
    token.save(update_fields=["revoked_at", "revogado_por", "deleted", "deleted_at"])

    ApiTokenLog.objects.create(
        token=token,
        usuario=usuario_log or revogado_por,
        acao=ApiTokenLog.Acao.REVOGACAO,
        ip=ip,
        user_agent=user_agent,
    )

    _send_webhook({"event": "revoked", "id": str(token.id)})
    return True


def rotate_token(
    token_id: uuid.UUID,
    revogado_por: User | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Gera novo token e revoga o anterior automaticamente."""

    token = ApiToken.objects.get(id=token_id)
    expires_in: timedelta | None = None
    if token.expires_at:
        delta = token.expires_at - timezone.now()
        if delta.total_seconds() > 0:
            expires_in = delta

    from .services import generate_token  # Lazy import to avoid circular dependency

    raw_token = generate_token(
        token.user,
        token.client_name,
        token.scope,
        expires_in,
    )
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    novo_token = ApiToken.objects.get(token_hash=token_hash)
    novo_token.anterior = token
    novo_token.save(update_fields=["anterior"])

    revoke_token(token.id, revogado_por, ip=ip, user_agent=user_agent)
    _send_webhook({"event": "rotated", "id": str(token.id), "new_id": str(novo_token.id)})
    return raw_token
