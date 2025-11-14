"""Authentication helpers for the accounts app."""

from __future__ import annotations

from typing import Optional

import pyotp

from .models import LoginAttempt
from tokens.models import TOTPDevice

TOTP_REQUIRED_MESSAGE = "Código de verificação obrigatório."
TOTP_INVALID_MESSAGE = "Código de verificação inválido."


def validate_totp(
    user,
    code: Optional[str],
    *,
    email: Optional[str] = None,
    ip: Optional[str] = None,
) -> Optional[str]:
    """Validate the ``code`` for ``user``'s 2FA configuration.

    Returns ``None`` when the verification succeeds or isn't required.
    Otherwise, returns the error message that should be presented to the user.
    When validation fails, the helper registers a ``LoginAttempt`` mirroring the
    behaviour expected by the existing authentication flows.
    """

    if not getattr(user, "two_factor_enabled", False):
        return None

    if not TOTPDevice.objects.filter(usuario=user).exists():
        return None

    if not getattr(user, "two_factor_secret", None):
        return _register_failure(user, email=email, ip=ip, message=TOTP_INVALID_MESSAGE)

    if not code:
        return _register_failure(user, email=email, ip=ip, message=TOTP_REQUIRED_MESSAGE)

    if not pyotp.TOTP(user.two_factor_secret).verify(code):
        return _register_failure(user, email=email, ip=ip, message=TOTP_INVALID_MESSAGE)

    return None


def _register_failure(user, *, email: Optional[str], ip: Optional[str], message: str) -> str:
    """Record a failed login attempt and return ``message``."""

    LoginAttempt.objects.create(
        usuario=user,
        email=email or getattr(user, "email", ""),
        sucesso=False,
        ip=ip,
    )
    return message


__all__ = ["validate_totp", "TOTP_INVALID_MESSAGE", "TOTP_REQUIRED_MESSAGE"]
