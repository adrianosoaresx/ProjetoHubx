import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import override_settings

from accounts.models import AccountToken, SecurityEvent

User = get_user_model()


@override_settings(ROOT_URLCONF="tests.urls_accounts")
@pytest.mark.django_db
def test_resend_confirmation_invalidates_previous_tokens(client):
    user = User.objects.create_user(email="u@example.com", username="u", is_active=False)
    old = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )
    resp = client.post("/resend-confirmation/", {"email": user.email})
    assert resp.status_code == 302
    old.refresh_from_db()
    assert old.used_at is not None
    tokens = AccountToken.objects.filter(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        used_at__isnull=True,
    )
    assert tokens.count() == 1
    assert tokens.first().expires_at > timezone.now()


@override_settings(ROOT_URLCONF="tests.urls_accounts")
@pytest.mark.django_db
def test_resend_confirmation_logs_security_event(client):
    user = User.objects.create_user(email="inactive@example.com", username="i", is_active=False)
    resp = client.post("/resend-confirmation/", {"email": user.email})
    assert resp.status_code == 302
    event = SecurityEvent.objects.get(usuario=user, evento="resend_confirmation")
    assert event.ip == "127.0.0.1"
