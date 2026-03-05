"""Authentication helpers for the accounts app."""

from __future__ import annotations

from typing import Optional

import pyotp
from django.core.cache import cache
from django.utils import timezone

from .models import LoginAttempt
from tokens.models import TOTPDevice

TOTP_REQUIRED_MESSAGE = "Código de verificação obrigatório."
TOTP_INVALID_MESSAGE = "Código de verificação inválido."
TOTP_UNAVAILABLE_MESSAGE = (
    "Não foi possível validar a autenticação em duas etapas. "
    "Reconfigure o 2FA na sua conta."
)

FAILED_LOGIN_TTL_SECONDS = 60 * 15
MAX_FAILED_LOGIN_ATTEMPTS = 3
LOCKOUT_MINUTES = 15


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

    if not TOTPDevice.objects.filter(usuario=user, confirmado=True).exists():
        return _register_failure(user, email=email, ip=ip, message=TOTP_UNAVAILABLE_MESSAGE)

    if not getattr(user, "two_factor_secret", None):
        return _register_failure(user, email=email, ip=ip, message=TOTP_UNAVAILABLE_MESSAGE)

    if not code:
        return _register_failure(user, email=email, ip=ip, message=TOTP_REQUIRED_MESSAGE)

    if not pyotp.TOTP(user.two_factor_secret).verify(code):
        return _register_failure(user, email=email, ip=ip, message=TOTP_INVALID_MESSAGE)

    return None


def _register_failure(user, *, email: Optional[str], ip: Optional[str], message: str) -> str:
    """Record a failed login attempt and return ``message``."""

    register_login_failure(user, email=email, ip=ip)
    return message


def _attempts_cache_key(user_id: int) -> str:
    return f"failed_login_attempts_user_{user_id}"


def _lockout_cache_key(user_id: int) -> str:
    return f"lockout_user_{user_id}"


def get_user_lockout_until(user) -> timezone.datetime | None:
    lock_until = cache.get(_lockout_cache_key(user.pk))
    if lock_until and lock_until > timezone.now():
        return lock_until
    return None


def clear_login_failures(user) -> None:
    cache.delete(_attempts_cache_key(user.pk))
    cache.delete(_lockout_cache_key(user.pk))


def register_login_failure(user, *, email: Optional[str], ip: Optional[str]) -> timezone.datetime | None:
    attempts_key = _attempts_cache_key(user.pk)
    attempts = cache.get(attempts_key, 0) + 1
    cache.set(attempts_key, attempts, FAILED_LOGIN_TTL_SECONDS)

    lock_until = None
    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        lock_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_MINUTES)
        cache.set(_lockout_cache_key(user.pk), lock_until, FAILED_LOGIN_TTL_SECONDS)

    LoginAttempt.objects.create(
        usuario=user,
        email=email or getattr(user, "email", ""),
        sucesso=False,
        ip=ip,
    )
    return lock_until


__all__ = [
    "clear_login_failures",
    "get_user_lockout_until",
    "register_login_failure",
    "validate_totp",
    "TOTP_INVALID_MESSAGE",
    "TOTP_REQUIRED_MESSAGE",
    "TOTP_UNAVAILABLE_MESSAGE",
]
