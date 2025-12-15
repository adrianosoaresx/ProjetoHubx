import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken
from accounts.tasks import send_password_reset_email

User = get_user_model()


@pytest.mark.django_db
def test_request_password_reset(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.FRONTEND_URL = "http://testserver"
    called = {}

    def fake_delay(token_id: int) -> None:
        called["id"] = token_id

    monkeypatch.setattr("accounts.tasks.send_password_reset_email.delay", fake_delay)
    user = User.objects.create_user(email="pw@example.com", username="pw")
    client = APIClient()
    url = reverse("accounts_api:account-request-password-reset")
    resp = client.post(url, {"email": "pw@example.com"})
    assert resp.status_code == 204
    first = AccountToken.objects.get(usuario=user, tipo=AccountToken.Tipo.PASSWORD_RESET)
    resp = client.post(url, {"email": "pw@example.com"})
    assert resp.status_code == 204
    second = AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.PASSWORD_RESET).exclude(id=first.id).get()
    first.refresh_from_db()
    assert first.used_at is not None
    assert called["id"] == second.id
    assert (
        AccountToken.objects.filter(
            usuario=user,
            tipo=AccountToken.Tipo.PASSWORD_RESET,
            used_at__isnull=True,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_send_password_reset_email_uses_backend_route(settings, monkeypatch):
    settings.FRONTEND_URL = "http://testserver"
    user = User.objects.create_user(email="route@example.com", username="route")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )

    captured = {}

    def fake_enviar_para_usuario(usuario, template, context):
        captured.update({"usuario": usuario, "template": template, "context": context})

    monkeypatch.setattr("accounts.tasks.enviar_para_usuario", fake_enviar_para_usuario)

    send_password_reset_email(token.id)

    assert captured["template"] == "password_reset"
    assert captured["usuario"] == user
    assert captured["context"]["url"] == f"http://testserver/accounts/password_reset/{token.codigo}/"
