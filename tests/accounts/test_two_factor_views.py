import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import SecurityEvent
from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
def test_enable_2fa_wrong_code_creates_security_event(client):
    user = User.objects.create_user(email="view2@example.com", username="v2", password="Strong!123")
    client.force_login(user)
    resp = client.get(reverse("tokens:ativar_2fa"))
    assert resp.status_code == 200

    resp = client.post(
        reverse("tokens:ativar_2fa"),
        {"codigo_totp": "000000"},
        HTTP_X_FORWARDED_FOR="1.1.1.2",
    )

    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitacao_falha", ip="1.1.1.2").exists()


@pytest.mark.django_db
def test_disable_2fa_logs_security_event(client):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="view3@example.com",
        username="v3",
        password="Strong!123",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    client.force_login(user)

    resp = client.post(
        reverse("tokens:desativar_2fa"),
        HTTP_X_FORWARDED_FOR="2.2.2.2",
    )

    assert resp.status_code == 302
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitado", ip="2.2.2.2").exists()
