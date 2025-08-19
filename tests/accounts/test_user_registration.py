import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.forms import CustomUserCreationForm
from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_user_creation_creates_inactive_and_token():
    form = CustomUserCreationForm(
        data={
            "email": "new@example.com",
            "cpf": "39053344705",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )
    assert form.is_valid(), form.errors
    user = form.save()
    assert not user.is_active
    assert user.failed_login_attempts == 0
    assert user.lock_expires_at is None
    token = AccountToken.objects.get(usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION)
    assert token.expires_at > timezone.now()


@pytest.mark.django_db
def test_user_creation_unique_email():
    User.objects.create_user(email="dup@example.com", username="dup", password="pass")
    form = CustomUserCreationForm(
        data={
            "email": "dup@example.com",
            "cpf": "39053344705",
            "password1": "StrongPass1!",
            "password2": "StrongPass1!",
        }
    )
    assert not form.is_valid()
    assert "email" in form.errors
