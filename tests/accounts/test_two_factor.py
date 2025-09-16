import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import SecurityEvent
from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
def test_enable_2fa_flow(client):
    user = User.objects.create_user(email="a@a.com", username="a", password="Strong!123")
    client.force_login(user)

    resp = client.get(reverse("tokens:ativar_2fa"))
    assert resp.status_code == 200
    user.refresh_from_db()
    totp = pyotp.TOTP(user.two_factor_secret).now()
    resp = client.post(reverse("tokens:ativar_2fa"), {"codigo_totp": totp})

    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled
    assert user.two_factor_secret
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitado").exists()


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
def test_check_2fa_neutral_response(client):
    cache.clear()
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="c@c.com", username="c", password="Strong!123", two_factor_enabled=True, two_factor_secret=secret
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    url = reverse("accounts:check_2fa")
    resp_existing = client.get(url + "?email=c@c.com")
    resp_missing = client.get(url + "?email=nao@existe.com")
    assert resp_existing.status_code == 204
    assert resp_missing.status_code == 204


@pytest.mark.django_db
def test_check_2fa_rate_limit(client):
    cache.clear()
    url = reverse("accounts:check_2fa") + "?email=foo@bar.com"
    for _ in range(5):
        resp = client.get(url)
        assert resp.status_code == 204
    resp = client.get(url)
    assert resp.status_code == 403


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
    resp = client.post(reverse("tokens:desativar_2fa"))
    assert resp.status_code == 302
    user.refresh_from_db()
    assert user.two_factor_enabled is False and user.two_factor_secret is None

    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitado").exists()


@pytest.mark.django_db
def test_enable_2fa_wrong_password_api():
    user = User.objects.create_user(email="e@e.com", username="e", password="Strong!123")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("accounts_api:account-enable-2fa"), {"password": "WrongPass1!"})
    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.two_factor_enabled is False
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitacao_falha").exists()


@pytest.mark.django_db
def test_disable_2fa_wrong_password_api():
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="f@f.com",
        username="f",
        password="Strong!123",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    client = APIClient()
    client.force_authenticate(user=user)
    code = pyotp.TOTP(secret).now()
    resp = client.post(
        reverse("accounts_api:account-disable-2fa"),
        {"code": code, "password": "WrongPass1!"},
    )
    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.two_factor_enabled is True
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitacao_falha").exists()
