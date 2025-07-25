from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

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
