from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import requests

from .models import WebhookEvent, WebhookSubscription


def create_subscription(user, url: str, secret: str) -> WebhookSubscription:
    """Cria uma inscrição de webhook para o usuário."""
    return WebhookSubscription.objects.create(user=user, url=url, secret=secret)


def revoke_subscription(subscription: WebhookSubscription) -> None:
    """Revoga uma inscrição de webhook."""
    subscription.revoke()


def emit_event(subscription: WebhookSubscription, event: str, payload: dict[str, Any]) -> WebhookEvent:
    """Cria um evento de webhook e agenda sua entrega."""
    webhook_event = WebhookEvent.objects.create(
        subscription=subscription, event=event, payload=payload
    )
    from .tasks import deliver_webhook

    deliver_webhook.delay(webhook_event.id)
    return webhook_event


def sign_payload(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def send_webhook(subscription: WebhookSubscription, payload: dict[str, Any]) -> requests.Response:
    """Envia um payload assinado para a URL do webhook."""
    data = json.dumps(payload).encode()
    signature = sign_payload(subscription.secret, data)
    headers = {"X-Hubx-Signature": signature, "Content-Type": "application/json"}
    return requests.post(subscription.url, data=data, headers=headers, timeout=10)
