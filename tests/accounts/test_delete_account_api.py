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


@pytest.mark.django_db
def test_cancel_delete_reactivates_user():
    user = User.objects.create_user(email="api_cancel@example.com", username="api_cancel", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    client.delete(reverse("accounts_api:account-delete-me"))
    user.refresh_from_db()
    assert not user.is_active
    resp = client.post(reverse("accounts_api:account-cancel-delete"))
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active
