from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Iterable, Tuple

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .metrics import (
    tokens_api_tokens_created_total,
    tokens_api_tokens_revoked_total,
)
from .models import ApiToken, TokenAcesso, TokenWebhookEvent

User = get_user_model()


# Rotinas de envio de webhooks -------------------------------------------------

def _send_webhook(payload: dict[str, object]) -> None:
    """Envia ``payload`` para o endpoint configurado.

    Caso todas as tentativas falhem, registra o evento para reprocessamento
    posterior em :class:`TokenWebhookEvent`.
    """

    url = getattr(settings, "TOKENS_WEBHOOK_URL", None)
    if not url:
        return

    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}

    secret = getattr(settings, "TOKEN_WEBHOOK_SECRET", "")
    if secret:
        signature = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
        headers["X-Hubx-Signature"] = signature

    attempts = 0
    delay = 1
    while attempts < 3:
        try:
            response = requests.post(url, data=data, headers=headers, timeout=5)
            if response.status_code < 400:
                return
        except Exception:  # pragma: no cover - falha de rede é ignorada
            pass
        attempts += 1
        if attempts < 3:
            time.sleep(delay)
            delay *= 2

    TokenWebhookEvent.objects.create(
        url=url,
        payload=payload,
        delivered=False,
        attempts=attempts,
        last_attempt_at=timezone.now(),
    )


def token_created(token: ApiToken, raw: str) -> None:
    """Dispara webhook para notificar criação de ``token``."""
    _send_webhook({"event": "created", "id": str(token.id), "token": raw})


def token_revoked(token: ApiToken) -> None:
    """Dispara webhook para notificar revogação de ``token``."""
    _send_webhook({"event": "revoked", "id": str(token.id)})


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

    tokens_api_tokens_created_total.inc()

    token_created(token, raw_token)

    return raw_token


def revoke_token(token_id: uuid.UUID, revogado_por: User | None = None) -> None:
    token = ApiToken.all_objects.get(id=token_id)
    if token.revoked_at:
        return
    now = timezone.now()
    token.revoked_at = now
    token.revogado_por = revogado_por or token.user
    token.deleted = True
    token.deleted_at = now
    token.save(update_fields=["revoked_at", "revogado_por", "deleted", "deleted_at"])

    tokens_api_tokens_revoked_total.inc()

    token_revoked(token)


def rotate_token(token_id: uuid.UUID, revogado_por: User | None = None) -> str:
    """Gera novo token e revoga o anterior automaticamente."""
    token = ApiToken.objects.get(id=token_id)
    expires_in: timedelta | None = None
    if token.expires_at:
        delta = token.expires_at - timezone.now()
        if delta.total_seconds() > 0:
            expires_in = delta

    raw_token = generate_token(token.user, token.client_name, token.scope, expires_in)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    novo_token = ApiToken.objects.get(token_hash=token_hash)
    novo_token.anterior = token
    novo_token.save(update_fields=["anterior"])
    revoke_token(token.id, revogado_por)
    return raw_token


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
    """Retorna o ``TokenAcesso`` correspondente ao ``codigo``.

    A busca é realizada apenas por meio do hash SHA-256, sem iteração
    adicional sobre tokens legados com ``codigo_salt``.
    """
    codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
    return TokenAcesso.objects.get(codigo_hash=codigo_hash)
