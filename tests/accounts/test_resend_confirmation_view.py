import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_resend_confirmation_invalidates_previous_tokens(client):
    user = User.objects.create_user(email="u@example.com", username="u", is_active=False)
    old = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )
    resp = client.post(reverse("accounts:resend_confirmation"), {"email": user.email})
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
