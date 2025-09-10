import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_clears_lock(client):
    user = User.objects.create_user(email="u@example.com", username="u")
    cache.set(f"failed_login_attempts_user_{user.pk}", 2, 900)
    cache.set(f"lockout_user_{user.pk}", timezone.now() + timezone.timedelta(minutes=30), 1800)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    url = reverse("accounts:password_reset_confirm", args=[token.codigo])
    resp = client.post(
        url,
        {"new_password1": "NovaSenha123", "new_password2": "NovaSenha123"},
    )
    assert resp.status_code in {200, 302}
    assert cache.get(f"failed_login_attempts_user_{user.pk}") is None
    assert cache.get(f"lockout_user_{user.pk}") is None
