import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
def test_enable_2fa_flow(client):
    user = User.objects.create_user(email="a@a.com", username="a", password="Strong!123")
    client.force_login(user)
    resp = client.get(reverse("accounts:enable_2fa"))
    assert resp.status_code == 200
    secret = client.session.get("tmp_2fa_secret")
    code = pyotp.TOTP(secret).now()
    resp = client.post(reverse("accounts:enable_2fa"), {"code": code})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled
    assert user.two_factor_secret


@pytest.mark.django_db
def test_login_requires_totp_when_enabled(client):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="b@b.com",
        username="b",
        password="Strong!123",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    url = reverse("accounts:login")
    resp = client.post(url, {"email": "b@b.com", "password": "Strong!123"})
    assert "Código de verificação obrigatório" in resp.content.decode()
    code = pyotp.TOTP(secret).now()
    resp = client.post(url, {"email": "b@b.com", "password": "Strong!123", "totp": code})
    assert resp.status_code == 302


@pytest.mark.django_db
def test_check_2fa_endpoint(client):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="c@c.com", username="c", password="Strong!123", two_factor_enabled=True, two_factor_secret=secret
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    url = reverse("accounts:check_2fa") + "?email=c@c.com"
    resp = client.get(url)
    assert resp.json()["enabled"] is True
    resp = client.get(reverse("accounts:check_2fa") + "?email=nao@existe.com")
    assert resp.json()["enabled"] is False


@pytest.mark.django_db
def test_disable_2fa_flow(client):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="d@d.com",
        username="d",
        password="Strong!123",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    client.force_login(user)
    code = pyotp.TOTP(secret).now()
    resp = client.post(reverse("accounts:disable_2fa"), {"code": code})
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled is False and user.two_factor_secret is None
