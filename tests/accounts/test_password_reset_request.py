import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AccountToken

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
    token = AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.PASSWORD_RESET).latest("created_at")
    assert called["id"] == token.id
