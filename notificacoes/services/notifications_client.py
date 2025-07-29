from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _post(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    resp = requests.post(url, json=payload, headers=headers or {}, timeout=10)
    resp.raise_for_status()


def send_email(user: Any, subject: str, body: str) -> None:
    url = settings.NOTIFICATIONS_EMAIL_API_URL
    key = settings.NOTIFICATIONS_EMAIL_API_KEY
    _post(url, {"to": user.email, "subject": subject, "body": body}, {"Authorization": f"Bearer {key}"})


def send_push(user: Any, message: str) -> None:
    url = settings.NOTIFICATIONS_PUSH_API_URL
    key = settings.NOTIFICATIONS_PUSH_API_KEY
    _post(url, {"user_id": user.id, "message": message}, {"Authorization": f"Bearer {key}"})


def send_whatsapp(user: Any, message: str) -> None:
    url = settings.NOTIFICATIONS_WHATSAPP_API_URL
    key = settings.NOTIFICATIONS_WHATSAPP_API_KEY
    _post(url, {"to": user.whatsapp, "message": message}, {"Authorization": f"Bearer {key}"})
