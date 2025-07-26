import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AccountToken

User = get_user_model()


@pytest.mark.django_db
def test_resend_and_confirm_email(settings, mailoutbox):
    settings.FRONTEND_URL = "http://testserver"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = User.objects.create_user(email="a@example.com", username="a", is_active=False)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("accounts_api:account-resend-confirmation")
    resp = client.post(url)
    assert resp.status_code == 204
    token = AccountToken.objects.filter(usuario=user, tipo=AccountToken.Tipo.EMAIL_CONFIRMATION).latest("created_at")
    assert token.expires_at > timezone.now()

    confirm_url = reverse("accounts_api:account-confirm-email")
    resp = client.post(confirm_url, {"token": token.codigo})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
