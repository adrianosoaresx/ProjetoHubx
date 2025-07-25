import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_account_token_expiration():
    user = User.objects.create_user(email="t@example.com", username="t")
    token = AccountToken.objects.create(
        usuario=user,
        tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
        expires_at=timezone.now() - timezone.timedelta(hours=1),
    )
    assert token.expires_at < timezone.now()
