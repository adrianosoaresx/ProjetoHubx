import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_reset_password_weak_password():
    user = User.objects.create_user(
        email="weak@example.com", username="weak", password="StrongPass1!"
    )
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    client = APIClient()
    url = reverse("accounts_api:account-reset-password")
    resp = client.post(url, {"token": token.codigo, "password": "Abc12345"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == ["A senha deve conter caracteres especiais."]
    user.refresh_from_db()
    assert user.check_password("StrongPass1!")
    token.refresh_from_db()
    assert token.used_at is None
