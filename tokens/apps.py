from django.apps import AppConfig
from django.conf import settings
from django.utils import timezone
import hashlib
import hmac
import json
import time
from typing import Any

import requests


class TokensConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tokens"

    def ready(self) -> None:
        """Configura callbacks para emissão de webhooks."""

        secret = getattr(settings, "TOKEN_WEBHOOK_SECRET", "")

        from .models import TokenWebhookEvent

        def _send(url: str | None, payload: dict[str, Any]) -> None:
            if not url:
                return
            data = json.dumps(payload).encode()
            headers = {"Content-Type": "application/json"}
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

        created_url = getattr(settings, "TOKEN_CREATED_WEBHOOK_URL", None)
        revoked_url = getattr(settings, "TOKEN_REVOKED_WEBHOOK_URL", None)

        from . import services

        def _created(token, raw_token: str) -> None:
            _send(created_url, {"id": str(token.id), "token": raw_token})

        def _revoked(token) -> None:
            _send(revoked_url, {"id": str(token.id)})

        services.token_created = _created
        services.token_revoked = _revoked
