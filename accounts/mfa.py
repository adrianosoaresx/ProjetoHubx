from __future__ import annotations

import secrets
import uuid

import pyotp
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tokens.models import TOTPDevice
from tokens.utils import get_client_ip

from .models import MFALoginChallenge

MFA_METHOD_TOTP = "totp"
MFA_METHOD_EMAIL_OTP = "email_otp"

MFA_EMAIL_CODE_LENGTH = 6
MFA_EMAIL_SEND_LIMIT = 3
MFA_EMAIL_SEND_WINDOW_MINUTES = 15
MFA_EMAIL_CHALLENGE_TTL_MINUTES = 5


def is_totp_enabled(user) -> bool:
    return bool(getattr(user, "two_factor_enabled", False))


def is_totp_available(user) -> bool:
    return (
        is_totp_enabled(user)
        and bool(getattr(user, "two_factor_secret", None))
        and TOTPDevice.objects.filter(usuario=user, confirmado=True).exists()
    )


def is_email_otp_enabled(user) -> bool:
    return bool(getattr(user, "two_factor_email_enabled", False))


def is_email_otp_available(user) -> bool:
    return is_email_otp_enabled(user) and bool((getattr(user, "email", "") or "").strip())


def has_enabled_mfa(user) -> bool:
    return is_totp_enabled(user) or is_email_otp_enabled(user)


def get_available_mfa_methods(user) -> list[str]:
    methods: list[str] = []
    if is_totp_available(user):
        methods.append(MFA_METHOD_TOTP)
    if is_email_otp_available(user):
        methods.append(MFA_METHOD_EMAIL_OTP)
    return methods


def has_blocking_mfa_misconfiguration(user) -> bool:
    if not has_enabled_mfa(user):
        return False
    return not get_available_mfa_methods(user)


def resolve_preferred_method(user, methods: list[str]) -> Optional[str]:
    if not methods:
        return None
    preferred = getattr(user, "two_factor_preferred_method", MFA_METHOD_TOTP)
    if preferred in methods:
        return preferred
    return methods[0]


def ensure_session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ""


def verify_totp_code(user, code: str | None) -> bool:
    if not is_totp_available(user):
        return False
    if not code:
        return False
    return bool(pyotp.TOTP(user.two_factor_secret).verify(code))


def _email_send_limit_cache_key(*, user_id: int, session_key: str, purpose: str) -> str:
    return f"mfa_email_send:{purpose}:{user_id}:{session_key}"


def issue_email_challenge(
    *,
    user,
    request,
    purpose: str = MFALoginChallenge.Purpose.LOGIN,
) -> MFALoginChallenge:
    if not is_email_otp_available(user):
        raise ValueError(_("2FA por e-mail não está disponível para esta conta."))

    session_key = ensure_session_key(request)
    now = timezone.now()

    cache_key = _email_send_limit_cache_key(
        user_id=user.pk,
        session_key=session_key,
        purpose=purpose,
    )
    send_count = int(cache.get(cache_key, 0))
    if send_count >= MFA_EMAIL_SEND_LIMIT:
        raise ValueError(_("Limite de envio atingido. Tente novamente em alguns minutos."))
    cache.set(cache_key, send_count + 1, MFA_EMAIL_SEND_WINDOW_MINUTES * 60)

    MFALoginChallenge.objects.filter(
        usuario=user,
        method=MFALoginChallenge.Method.EMAIL_OTP,
        purpose=purpose,
        session_key=session_key,
        used_at__isnull=True,
    ).update(used_at=now)

    code = f"{secrets.randbelow(10 ** MFA_EMAIL_CODE_LENGTH):0{MFA_EMAIL_CODE_LENGTH}d}"
    challenge = MFALoginChallenge(
        usuario=user,
        method=MFALoginChallenge.Method.EMAIL_OTP,
        purpose=purpose,
        expires_at=now + timezone.timedelta(minutes=MFA_EMAIL_CHALLENGE_TTL_MINUTES),
        max_attempts=5,
        session_key=session_key,
        ip=get_client_ip(request),
    )
    challenge.set_code(code)
    challenge.save()

    from .tasks import send_mfa_email_code

    try:
        send_mfa_email_code.delay(user.pk, code, purpose)
    except Exception as exc:  # pragma: no cover - integração externa
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        raise ValueError(_("Não foi possível enviar o código por e-mail neste momento.")) from exc
    return challenge


def get_active_email_challenge(
    *,
    user,
    request,
    purpose: str,
    challenge_id: str | None = None,
) -> MFALoginChallenge | None:
    session_key = ensure_session_key(request)
    queryset = MFALoginChallenge.objects.filter(
        usuario=user,
        method=MFALoginChallenge.Method.EMAIL_OTP,
        purpose=purpose,
        session_key=session_key,
        used_at__isnull=True,
    ).order_by("-created_at")
    if challenge_id:
        try:
            challenge_id = str(uuid.UUID(str(challenge_id)))
        except (TypeError, ValueError):
            return None
        queryset = queryset.filter(pk=challenge_id)
    challenge = queryset.first()
    if not challenge:
        return None
    if challenge.is_expired():
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        return None
    return challenge


def verify_email_challenge(
    *,
    user,
    request,
    code: str | None,
    purpose: str,
    challenge_id: str | None = None,
) -> tuple[bool, str | None]:
    challenge = get_active_email_challenge(
        user=user,
        request=request,
        purpose=purpose,
        challenge_id=challenge_id,
    )
    if not challenge:
        return False, _("Código expirado ou não solicitado.")
    if challenge.attempts >= challenge.max_attempts:
        return False, _("Código bloqueado por excesso de tentativas.")
    if not code or not challenge.check_code(code):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        if challenge.attempts >= challenge.max_attempts:
            return False, _("Código bloqueado por excesso de tentativas.")
        return False, _("Código inválido.")
    challenge.used_at = timezone.now()
    challenge.save(update_fields=["used_at"])
    return True, None
