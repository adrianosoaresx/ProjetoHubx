import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.simple_urls")
@freeze_time("2024-01-01 12:00:00")
def test_delete_me_sets_user_inactive():
    user = User.objects.create_user(email="api_del@example.com", username="api_del", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.delete(reverse("account-delete-me", urlconf="accounts.api_urls"))
    assert resp.status_code == 204
    user.refresh_from_db()
    assert not user.is_active
    assert user.deleted and user.deleted_at is not None
    assert user.exclusao_confirmada
    token = user.account_tokens.get(tipo="cancel_delete")
    assert token.expires_at == timezone.now() + timezone.timedelta(days=30)


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.simple_urls")
def test_cancel_delete_reactivates_user():
    user = User.objects.create_user(email="api_cancel@example.com", username="api_cancel", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    client.delete(reverse("account-delete-me", urlconf="accounts.api_urls"))
    user.refresh_from_db()
    assert not user.is_active and user.deleted
    token = user.account_tokens.get(tipo="cancel_delete")
    client = APIClient()
    resp = client.post(
        reverse("account-cancel-delete", urlconf="accounts.api_urls"),
        {"token": token.codigo},
        format="json",
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert not user.deleted and user.deleted_at is None
