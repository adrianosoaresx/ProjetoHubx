from __future__ import annotations

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

