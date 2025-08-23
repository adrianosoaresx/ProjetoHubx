from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from freezegun import freeze_time

from accounts.models import AccountToken, SecurityEvent
from accounts.forms import CustomUserCreationForm

User = get_user_model()


@pytest.mark.django_db
def test_confirmation_token_expiry(client):
    user = User.objects.create_user(email="exp@example.com", username="exp", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() - timezone.timedelta(seconds=1),
    )
    url = reverse("accounts:confirmar_email", args=[token.codigo])
    client.get(url)
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmacao_falha").exists()


@pytest.mark.django_db
def test_password_reset_token_expiry(client):
    user = User.objects.create_user(email="reset@example.com", username="reset")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() - timezone.timedelta(seconds=1),
    )
    url = reverse("accounts:password_reset_confirm", args=[token.codigo])
    client.get(url, follow=True)
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinicao_falha").exists()


@pytest.mark.django_db
def test_confirmation_token_not_reusable(client):
    user = User.objects.create_user(email="n@example.com", username="n", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    url = reverse("accounts:confirmar_email", args=[token.codigo])
    client.get(url)
    client.get(url)
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmado").count() == 1
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmacao_falha").count() == 1


@pytest.mark.django_db
def test_password_reset_token_not_reusable(client):
    user = User.objects.create_user(email="pr@example.com", username="pr", password="old")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    url = reverse("accounts:password_reset_confirm", args=[token.codigo])
    client.post(url, {"new_password1": "Newpass123!", "new_password2": "Newpass123!"})
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinida").count() == 1
    client.post(url, {"new_password1": "Other123!", "new_password2": "Other123!"})
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinicao_falha").count() == 1


@pytest.mark.django_db
def test_resend_confirmation_invalidates_previous(client, monkeypatch):
    user = User.objects.create_user(email="r@example.com", username="r", is_active=False)
    old = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    monkeypatch.setattr(
        "accounts.tasks.send_confirmation_email.delay", lambda *a, **k: None
    )
    client.post(reverse("accounts:resend_confirmation"), {"email": user.email})
    assert (
        AccountToken.objects.filter(
            usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION, used_at__isnull=True
        ).count()
        == 1
    )
    old.refresh_from_db()
    assert old.used_at is not None


@pytest.mark.django_db
def test_confirmation_token_default_expiry_and_invalidation(client):
    with freeze_time("2024-01-01 12:00:00"):
        form = CustomUserCreationForm(
            data={
                "email": "time@example.com",
                "cpf": "39053344705",
                "password1": "StrongPass1!",
                "password2": "StrongPass1!",
            }
        )
        assert form.is_valid(), form.errors
        user = form.save()
        token = AccountToken.objects.get(
            usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION
        )
        assert token.expires_at == timezone.now() + timezone.timedelta(hours=24)

    with freeze_time("2024-01-02 12:00:01"):
        url = reverse("accounts:confirmar_email", args=[token.codigo])
        client.get(url)
        assert SecurityEvent.objects.filter(
            usuario=user, evento="email_confirmacao_falha"
        ).exists()


@pytest.mark.django_db
def test_password_reset_token_default_expiry_and_invalidation(client, monkeypatch):
    user = User.objects.create_user(email="reset2@example.com", username="reset2")
    with freeze_time("2024-01-01 12:00:00"):
        monkeypatch.setattr(
            "accounts.tasks.send_password_reset_email.delay", lambda *a, **k: None
        )
        client.post(reverse("accounts:password_reset"), {"email": user.email})
        assert SecurityEvent.objects.filter(
            usuario=user, evento="senha_reset_solicitada"
        ).exists()
        token = AccountToken.objects.get(
            usuario=user, tipo=AccountToken.Tipo.PASSWORD_RESET
        )
        assert token.expires_at == timezone.now() + timezone.timedelta(hours=1)

    with freeze_time("2024-01-01 13:00:01"):
        url = reverse("accounts:password_reset_confirm", args=[token.codigo])
        client.get(url, follow=True)
        assert SecurityEvent.objects.filter(
            usuario=user, evento="senha_redefinicao_falha"
        ).exists()

