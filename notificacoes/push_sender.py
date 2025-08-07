from __future__ import annotations

from typing import Any, Iterable

from django.conf import settings
from pywebpush import WebPushException, webpush

from .models import PushSubscription


def send(user, payload: Any, device_ids: Iterable[str] | None = None) -> None:
    """Envia notificações Web Push para as inscrições do usuário.

    Marca a inscrição como inativa se o endpoint retornar 404 ou 410.
    """

    subs = PushSubscription.objects.filter(user=user, active=True)
    if device_ids is not None:
        subs = subs.filter(device_id__in=list(device_ids))
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=getattr(settings, "VAPID_PRIVATE_KEY", None),
                vapid_claims={"sub": getattr(settings, "VAPID_CLAIM_SUB", "mailto:admin@example.com")},
            )
        except WebPushException as exc:  # pragma: no cover - lib externa
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                sub.active = False
                sub.save(update_fields=["active"])
            else:
                raise
