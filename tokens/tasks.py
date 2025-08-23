from __future__ import annotations

import hashlib
import hmac
import json
import time

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ApiToken, ApiTokenLog, TokenUsoLog, TokenWebhookEvent


@shared_task
def remover_logs_antigos() -> None:
    limite = timezone.now() - timezone.timedelta(days=365)
    TokenUsoLog.all_objects.filter(created_at__lt=limite).delete()
    ApiTokenLog.all_objects.filter(created_at__lt=limite).delete()


@shared_task
def revogar_tokens_expirados() -> None:
    now = timezone.now()

    tokens = ApiToken.objects.filter(expires_at__lt=now, revoked_at__isnull=True)
    for token in tokens:
        token.revoked_at = now
        token.revogado_por = token.user  # automatic revocation by owner, if any
        token.deleted = True
        token.deleted_at = now
        token.save(update_fields=["revoked_at", "revogado_por", "deleted", "deleted_at"])
        ApiTokenLog.objects.create(
            token=token,
            usuario=None,
            acao=ApiTokenLog.Acao.REVOGACAO,
            ip="0.0.0.0",
            user_agent="task:revogar_tokens_expirados",
        )


@shared_task
def send_webhook(payload: dict[str, object]) -> None:
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


@shared_task
def reenviar_webhooks_pendentes() -> None:
    secret = getattr(settings, "TOKEN_WEBHOOK_SECRET", "")
    eventos = TokenWebhookEvent.objects.filter(delivered=False)
    for evento in eventos:
        data = json.dumps(evento.payload).encode()
        headers = {"Content-Type": "application/json"}
        if secret:
            signature = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
            headers["X-Hubx-Signature"] = signature

        attempts = 0
        delay = 1
        sucesso = False
        while attempts < 3:
            try:
                response = requests.post(evento.url, data=data, headers=headers, timeout=5)
                if response.status_code < 400:
                    sucesso = True
                    break
            except Exception:  # pragma: no cover
                pass
            attempts += 1
            if attempts < 3:
                time.sleep(delay)
                delay *= 2

        evento.attempts += attempts
        evento.last_attempt_at = timezone.now()
        if sucesso:
            evento.delivered = True
        evento.save(update_fields=["delivered", "attempts", "last_attempt_at"])
