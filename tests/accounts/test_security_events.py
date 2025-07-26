import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken, SecurityEvent

User = get_user_model()


@pytest.mark.django_db
def test_security_events_flow():
    user = User.objects.create_user(email="sec@example.com", username="sec", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)

    # enable 2FA
    resp = client.post(reverse("accounts_api:account-enable-2fa"))
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitado").exists()

    # disable 2FA
    resp = client.post(reverse("accounts_api:account-disable-2fa"))
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitado").exists()

    # delete account
    resp = client.delete(reverse("accounts_api:account-delete-me"))
    assert resp.status_code == 204
    assert SecurityEvent.objects.filter(usuario=user, evento="conta_excluida").exists()

    # cancel deletion
    resp = client.post(reverse("accounts_api:account-cancel-delete"))
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="cancelou_exclusao").exists()


@pytest.mark.django_db
def test_reset_password_logs_security_event():
    user = User.objects.create_user(email="reset@example.com", username="r", password="old")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    client = APIClient()
    url = reverse("accounts_api:account-reset-password")
    resp = client.post(url, {"token": token.codigo, "password": "newpass"})
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinida").exists()
