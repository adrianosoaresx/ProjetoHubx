import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import SecurityEvent
from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
def test_enable_2fa_wrong_password_creates_security_event(client, monkeypatch):
    user = User.objects.create_user(email="view1@example.com", username="v1", password="Strong!123")
    client.force_login(user)
    secret = pyotp.random_base32()
    session = client.session
    session["tmp_2fa_secret"] = secret
    session.save()
    code = pyotp.TOTP(secret).now()
    monkeypatch.setattr(pyotp.TOTP, "verify", lambda self, code: True)

    resp = client.post(
        reverse("accounts:enable_2fa"),
        {"password": "Wrong!123", "code": code},
        HTTP_X_FORWARDED_FOR="1.1.1.1",
    )

    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitacao_falha", ip="1.1.1.1").exists()


@pytest.mark.django_db
def test_enable_2fa_wrong_code_creates_security_event(client, monkeypatch):
    user = User.objects.create_user(email="view2@example.com", username="v2", password="Strong!123")
    client.force_login(user)
    secret = pyotp.random_base32()
    session = client.session
    session["tmp_2fa_secret"] = secret
    session.save()
    monkeypatch.setattr(pyotp.TOTP, "verify", lambda self, code: False)

    resp = client.post(
        reverse("accounts:enable_2fa"),
        {"password": "Strong!123", "code": "000000"},
        HTTP_X_FORWARDED_FOR="1.1.1.2",
    )

    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitacao_falha", ip="1.1.1.2").exists()


@pytest.mark.django_db
def test_disable_2fa_wrong_password_creates_security_event(client, monkeypatch):
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
    code = pyotp.TOTP(secret).now()
    monkeypatch.setattr(pyotp.TOTP, "verify", lambda self, code: True)

    resp = client.post(
        reverse("accounts:disable_2fa"),
        {"password": "Wrong!123", "code": code},
        HTTP_X_FORWARDED_FOR="2.2.2.2",
    )

    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitacao_falha", ip="2.2.2.2").exists()


@pytest.mark.django_db
def test_disable_2fa_wrong_code_creates_security_event(client, monkeypatch):
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="view4@example.com",
        username="v4",
        password="Strong!123",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)
    client.force_login(user)
    monkeypatch.setattr(pyotp.TOTP, "verify", lambda self, code: False)

    resp = client.post(
        reverse("accounts:disable_2fa"),
        {"password": "Strong!123", "code": "000000"},
        HTTP_X_FORWARDED_FOR="2.2.2.3",
    )

    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitacao_falha", ip="2.2.2.3").exists()
