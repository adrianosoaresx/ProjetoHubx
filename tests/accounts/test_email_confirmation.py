import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken, SecurityEvent
from accounts.tasks import send_confirmation_email

User = get_user_model()


@pytest.mark.django_db
def test_resend_and_confirm_email(settings, mailoutbox):
    settings.FRONTEND_URL = "http://testserver"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = User.objects.create_user(email="a@example.com", username="a", is_active=False)
    client = APIClient()
    url = reverse("accounts_api:account-resend-confirmation")
    resp = client.post(url, {"email": user.email})
    assert resp.status_code == 204
    token = AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION).latest("created_at")
    assert token.expires_at > timezone.now()

    confirm_url = reverse("accounts_api:account-confirm-email")
    resp = client.post(confirm_url, {"token": token.codigo})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert user.email_confirmed is True


@pytest.mark.django_db
def test_confirm_email_api_handles_expired_token():
    user = User.objects.create_user(email="expired@example.com", username="expired", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() - timezone.timedelta(seconds=1),
    )
    client = APIClient()
    url = reverse("accounts_api:account-confirm-email")
    resp = client.post(url, {"token": token.codigo})
    assert resp.status_code == 400
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmacao_falha").exists()
    token.refresh_from_db()
    assert token.status == AccountToken.Status.PENDENTE
    assert token.used_at is None


@pytest.mark.django_db
def test_confirm_email_api_marks_token_used():
    user = User.objects.create_user(email="ok@example.com", username="ok", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    client = APIClient()
    url = reverse("accounts_api:account-confirm-email")
    resp = client.post(url, {"token": token.codigo})
    assert resp.status_code == 200
    token.refresh_from_db()
    assert token.status == AccountToken.Status.UTILIZADO
    assert token.used_at is not None


@pytest.mark.django_db
def test_send_confirmation_email_logs_event(settings, monkeypatch):
    settings.FRONTEND_URL = "http://testserver"
    user = User.objects.create_user(email="notify@example.com", username="notify")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
        ip_gerado="127.0.0.1",
    )
    monkeypatch.setattr("accounts.tasks.enviar_para_usuario", lambda *args, **kwargs: None)

    send_confirmation_email(token.id)

    assert SecurityEvent.objects.filter(
        usuario=user, evento="email_confirmacao_enviado", ip="127.0.0.1"
    ).exists()


@pytest.mark.django_db
def test_confirm_email_view_accepts_querystring_token(client):
    user = User.objects.create_user(email="query@example.com", username="query", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )

    url = reverse("accounts:confirm_email") + f"?token={token.codigo}"

    response = client.get(url)

    assert response.status_code == 200

    user.refresh_from_db()
    token.refresh_from_db()

    assert user.is_active is True
    assert user.email_confirmed is True
    assert token.status == AccountToken.Status.UTILIZADO
