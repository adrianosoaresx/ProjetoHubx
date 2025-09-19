from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


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
