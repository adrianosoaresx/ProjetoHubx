"""Simple wrapper for the platform notification service."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def send_email(user: Any, subject: str, body: str) -> None:
    """Send email notification (placeholder)."""
    logger.info("[notif] email to %s: %s", getattr(user, "email", "?"), subject)
    # TODO: integrate with real notification service


def send_push(user: Any, message: str) -> None:
    """Send push notification (placeholder)."""
    logger.info("[notif] push to %s: %s", getattr(user, "id", "?"), message)


def send_whatsapp(user: Any, message: str) -> None:
    """Send WhatsApp notification (placeholder)."""
    logger.info("[notif] WhatsApp to %s: %s", getattr(user, "phone", "?"), message)
