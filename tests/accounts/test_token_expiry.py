from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken, SecurityEvent

User = get_user_model()


@pytest.mark.django_db
def test_confirmation_token_expired(client):
    user = User.objects.create_user(email="exp@example.com", username="exp", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() - timezone.timedelta(hours=24, seconds=1),
    )
    url = reverse("accounts:confirmar_email", args=[token.codigo])
    client.get(url)
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmacao_falha").exists()


@pytest.mark.django_db
def test_confirmation_token_within_valid_period(client):
    user = User.objects.create_user(email="exp2@example.com", username="exp2", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(minutes=1),
    )
    url = reverse("accounts:confirmar_email", args=[token.codigo])
    client.get(url)
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmado").exists()


@pytest.mark.django_db
def test_password_reset_token_expired(client):
    user = User.objects.create_user(email="reset@example.com", username="reset")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() - timezone.timedelta(hours=1, seconds=1),
    )
    url = reverse("accounts:password_reset_confirm", args=[token.codigo])
    client.get(url, follow=True)
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinicao_falha").exists()


@pytest.mark.django_db
def test_password_reset_token_within_valid_period(client):
    user = User.objects.create_user(email="reset2@example.com", username="reset2")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(minutes=1),
    )
    url = reverse("accounts:password_reset_confirm", args=[token.codigo])
    client.post(url, {"new_password1": "Newpass123!", "new_password2": "Newpass123!"})
    assert SecurityEvent.objects.filter(usuario=user, evento="senha_redefinida").exists()


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
def test_resend_confirmation_invalidates_previous(client, mocker):
    user = User.objects.create_user(email="r@example.com", username="r", is_active=False)
    old = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    mocker.patch("accounts.tasks.send_confirmation_email.delay")
    client.post(reverse("accounts:resend_confirmation"), {"email": user.email})
    assert AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION, used_at__isnull=True).count() == 1
    old.refresh_from_db()
    assert old.used_at is not None


@pytest.mark.django_db
def test_account_token_entropy():
    user = User.objects.create_user(email="ent@example.com", username="ent")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
    )
    assert len(token.codigo) >= 43

