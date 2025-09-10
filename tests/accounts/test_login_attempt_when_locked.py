import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

from accounts.forms import EmailLoginForm
from accounts.models import LoginAttempt, SecurityEvent


User = get_user_model()


@pytest.mark.django_db
def test_login_attempt_created_when_account_locked(rf):
    user = User.objects.create_user(email="lock@example.com", username="lock", password="pass")
    cache.set(
        f"lockout_user_{user.pk}",
        timezone.now() + timezone.timedelta(minutes=1),
        60,
    )

    request = rf.post(
        "/login/",
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_FORWARDED_FOR="2.2.2.2",
    )
    form = EmailLoginForm(request, data={"email": "lock@example.com", "password": "pass"})

    assert not form.is_valid()
    assert LoginAttempt.objects.filter(usuario=user, sucesso=False).count() == 1
    assert SecurityEvent.objects.filter(
        usuario=user,
        evento="login_bloqueado",
        ip="2.2.2.2",
    ).exists()
