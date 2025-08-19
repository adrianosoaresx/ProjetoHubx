from __future__ import annotations

import json

import requests
from celery import shared_task
from django.utils import timezone

from .models import WebhookEvent
from .services import sign_payload


@shared_task(bind=True, max_retries=5)
def deliver_webhook(self, event_id: str) -> None:
    event = WebhookEvent.objects.select_related("subscription").get(id=event_id)
    subscription = event.subscription
    payload = event.payload
    data = json.dumps(payload).encode()
    signature = sign_payload(subscription.secret, data)
    headers = {"X-Hubx-Signature": signature, "Content-Type": "application/json"}

    try:
        response = requests.post(subscription.url, data=data, headers=headers, timeout=10)
        if response.status_code >= 400:
            raise requests.RequestException(f"Status {response.status_code}")
    except Exception as exc:  # pragma: no cover - network failure paths
        event.attempts += 1
        event.last_attempt_at = timezone.now()
        event.save(update_fields=["attempts", "last_attempt_at"])
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)

    event.delivered = True
    event.attempts += 1
    event.last_attempt_at = timezone.now()
    event.save(update_fields=["delivered", "attempts", "last_attempt_at"])
