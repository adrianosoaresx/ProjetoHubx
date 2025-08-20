import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_delete_me_sets_user_inactive():
    user = User.objects.create_user(email="api_del@example.com", username="api_del", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.delete(reverse("accounts_api:account-delete-me"))
    assert resp.status_code == 204
    user.refresh_from_db()
    assert not user.is_active
    assert user.deleted and user.deleted_at is not None
    assert user.exclusao_confirmada
    assert user.account_tokens.filter(tipo="cancel_delete").exists()


@pytest.mark.django_db
def test_cancel_delete_reactivates_user():
    user = User.objects.create_user(email="api_cancel@example.com", username="api_cancel", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    client.delete(reverse("accounts_api:account-delete-me"))
    user.refresh_from_db()
    assert not user.is_active and user.deleted
    token = user.account_tokens.get(tipo="cancel_delete")
    client = APIClient()
    resp = client.post(
        reverse("accounts_api:account-cancel-delete"),
        {"token": token.codigo},
        format="json",
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
    assert not user.deleted and user.deleted_at is None
