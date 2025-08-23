import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken, SecurityEvent
from tokens.models import TOTPDevice

User = get_user_model()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls_accounts_plus")
def test_security_events_flow(monkeypatch):
    user = User.objects.create_user(email="sec@example.com", username="sec", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    monkeypatch.setattr("accounts.tasks.send_cancel_delete_email.delay", lambda *args, **kwargs: None)

    # enable 2FA
    resp = client.post(reverse("accounts_api:account-enable-2fa"), {"password": "pass"})
    assert resp.status_code == 200
    secret = resp.json()["secret"]
    totp = pyotp.TOTP(secret).now()
    resp = client.post(
        reverse("accounts_api:account-enable-2fa"),
        {"code": totp, "password": "pass"},
    )
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_habilitado").exists()

    # disable 2FA
    disable_code = pyotp.TOTP(secret).now()
    resp = client.post(
        reverse("accounts_api:account-disable-2fa"),
        {"code": disable_code, "password": "pass"},
    )
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="2fa_desabilitado").exists()

    # delete account
    resp = client.delete(
        reverse("accounts_api:account-delete-me"),
        {"password": "pass"},
        format="json",
    )
    assert resp.status_code == 204
    assert SecurityEvent.objects.filter(usuario=user, evento="conta_excluida").exists()

    # cancel deletion
    token = user.account_tokens.get(tipo="cancel_delete")
    resp = client.post(
        reverse("accounts_api:account-cancel-delete"),
        {"token": token.codigo},
        format="json",
    )
    assert resp.status_code == 200
    assert SecurityEvent.objects.filter(usuario=user, evento="cancelou_exclusao").exists()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls_accounts_plus")
def test_reset_password_logs_security_event():
    user = User.objects.create_user(email="reset@example.com", username="r", password="old")
    user.failed_login_attempts = 3
    user.lock_expires_at = timezone.now() + timezone.timedelta(minutes=30)
    user.save()
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    client = APIClient()
    url = reverse("accounts_api:account-reset-password")
    resp = client.post(url, {"token": token.codigo, "password": "newpass"})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.lock_expires_at is None
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinida").exists()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls_accounts_plus")
def test_resend_confirmation_logs_security_event():
    user = User.objects.create_user(email="inactive@example.com", username="i", is_active=False)
    client = APIClient()
    resp = client.post(reverse("accounts_api:account-resend-confirmation"), {"email": user.email})
    assert resp.status_code == 204
    assert resp.wsgi_request.user.is_anonymous
    assert SecurityEvent.objects.filter(usuario=user, evento="resend_confirmation").exists()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls_accounts_plus")
def test_disable_2fa_requires_code():
    user = User.objects.create_user(email="tfa@example.com", username="t", password="pass", two_factor_enabled=True, two_factor_secret=pyotp.random_base32())
    TOTPDevice.objects.create(usuario=user, secret=user.two_factor_secret, confirmado=True)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("accounts_api:account-disable-2fa"), {"password": "pass"})
    assert resp.status_code == 400
