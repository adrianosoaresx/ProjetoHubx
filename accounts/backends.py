import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

from tokens.models import TOTPDevice

from .models import LoginAttempt


class EmailBackend(ModelBackend):
    """Autentica usando email de forma case-insensitive."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username:
            return None
        ip = request.META.get("REMOTE_ADDR") if request else None
        try:
            user = UserModel._default_manager.get(email__iexact=username)
        except UserModel.DoesNotExist:
            LoginAttempt.objects.create(email=username, sucesso=False, ip=ip)
            return None
        now = timezone.now()
        if user.lock_expires_at and user.lock_expires_at > now:
            LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            if user.two_factor_enabled and TOTPDevice.objects.filter(usuario=user).exists():
                totp_code = kwargs.get("totp") or (request.POST.get("totp") if request else None)
                if not totp_code or not pyotp.TOTP(user.two_factor_secret).verify(totp_code):
                    LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
                    return None
            user.failed_login_attempts = 0
            user.lock_expires_at = None
            user.save(update_fields=["failed_login_attempts", "lock_expires_at"])
            LoginAttempt.objects.create(usuario=user, email=username, sucesso=True, ip=ip)
            return user
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 3:
            user.lock_expires_at = now + timezone.timedelta(minutes=15)
        user.save(update_fields=["failed_login_attempts", "lock_expires_at"])
        LoginAttempt.objects.create(usuario=user, email=username, sucesso=False, ip=ip)
        return None
