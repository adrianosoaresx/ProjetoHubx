import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken, SecurityEvent

User = get_user_model()


@pytest.mark.django_db
def test_email_confirm_view_success(client):
    user = User.objects.create_user(email="c@example.com", username="c", is_active=False)
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    url = reverse("accounts:confirmar_email", args=[token.codigo])
    resp = client.get(url)
    assert resp.status_code == 200
    token.refresh_from_db()
    user.refresh_from_db()
    assert token.used_at is not None
    assert user.is_active
    assert SecurityEvent.objects.filter(usuario=user, evento="email_confirmado").exists()


@pytest.mark.django_db
def test_email_confirm_view_error(client):
    url = reverse("accounts:confirmar_email", args=["invalid"])
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Link inv\xc3\xa1lido" in resp.content
