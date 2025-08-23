import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.urls")
def test_password_change_marks_reset_tokens_used(client):
    user = User.objects.create_user(email="pc@example.com", username="pc", password="oldpass")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.PASSWORD_RESET,
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    client.force_login(user)
    resp = client.post(
        reverse("accounts:seguranca"),
        {
            "old_password": "oldpass",
            "new_password1": "Newpass123!",
            "new_password2": "Newpass123!",
        },
    )
    assert resp.status_code == 302
    token.refresh_from_db()
    assert token.used_at is not None
