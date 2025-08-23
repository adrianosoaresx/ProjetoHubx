import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.utils import timezone

from tokens.models import TOTPDevice

from .models import LoginAttempt
from tokens.utils import get_client_ip


class EmailBackend(ModelBackend):
    """Autentica usando email de forma case-insensitive."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username:
            return None
        ip = get_client_ip(request) if request else None
        ip_lock_key = f"lockout_ip_{ip}" if ip else None
        now = timezone.now()
        if ip_lock_key and cache.get(ip_lock_key):
            LoginAttempt.objects.create(email=username, sucesso=False, ip=ip)
            return None
        try:
            user = UserModel._default_manager.get(email__iexact=username)
        except UserModel.DoesNotExist:
            LoginAttempt.objects.create(email=username, sucesso=False, ip=ip)
            if ip:
                attempts_key = f"failed_login_attempts_ip_{ip}"
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, 60 * 15)
                if attempts >= 3:
                    cache.set(ip_lock_key, now + timezone.timedelta(minutes=15), 60 * 15)
            return None
        user_lock_key = f"lockout_user_{user.pk}"
        lock_until = cache.get(user_lock_key)
        if lock_until and lock_until > now:
            LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            if user.two_factor_enabled and TOTPDevice.objects.filter(usuario=user).exists():
                totp_code = kwargs.get("totp") or (request.POST.get("totp") if request else None)
                if not totp_code or not pyotp.TOTP(user.two_factor_secret).verify(totp_code):
                    LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
                    return None
            cache.delete(f"failed_login_attempts_user_{user.pk}")
            cache.delete(user_lock_key)
            LoginAttempt.objects.create(usuario=user, email=username, sucesso=True, ip=ip)
            return user
        attempts_key = f"failed_login_attempts_user_{user.pk}"
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, 60 * 15)
        if attempts >= 3:
            cache.set(user_lock_key, now + timezone.timedelta(minutes=15), 60 * 15)
        LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
        return None
