import pyotp
import pytest
from django.contrib.auth import get_user_model

from accounts.auth import (
    TOTP_INVALID_MESSAGE,
    TOTP_REQUIRED_MESSAGE,
    validate_totp,
)
from accounts.models import LoginAttempt
from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
def test_validate_totp_skips_when_not_enabled():
    user = User.objects.create_user(email="no2fa@example.com", username="no2fa", password="pass")

    assert validate_totp(user, None) is None
    assert LoginAttempt.objects.count() == 0


@pytest.mark.django_db
def test_validate_totp_requires_code_and_logs_attempt():
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="missing@example.com",
        username="missing",
        password="pass",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)

    message = validate_totp(user, "", email="custom@example.com", ip="1.1.1.1")

    assert message == TOTP_REQUIRED_MESSAGE
    attempt = LoginAttempt.objects.get()
    assert attempt.usuario == user
    assert attempt.email == "custom@example.com"
    assert attempt.ip == "1.1.1.1"
    assert attempt.sucesso is False


@pytest.mark.django_db
def test_validate_totp_invalid_code_logs_attempt():
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="invalid@example.com",
        username="invalid",
        password="pass",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)

    message = validate_totp(user, "123456", email=user.email, ip="2.2.2.2")

    assert message == TOTP_INVALID_MESSAGE
    attempt = LoginAttempt.objects.get()
    assert attempt.usuario == user
    assert attempt.email == user.email
    assert attempt.ip == "2.2.2.2"
    assert attempt.sucesso is False


@pytest.mark.django_db
def test_validate_totp_accepts_valid_code():
    secret = pyotp.random_base32()
    user = User.objects.create_user(
        email="valid@example.com",
        username="valid",
        password="pass",
        two_factor_enabled=True,
        two_factor_secret=secret,
    )
    TOTPDevice.objects.create(usuario=user, secret=secret, confirmado=True)

    valid_code = pyotp.TOTP(secret).now()

    assert validate_totp(user, valid_code, email=user.email) is None
    assert LoginAttempt.objects.count() == 0
