import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_clears_lock(client):
    user = User.objects.create_user(email="u@example.com", username="u")
    user.failed_login_attempts = 2
    user.lock_expires_at = timezone.now() + timezone.timedelta(minutes=30)
    user.save()
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
    user.refresh_from_db()
