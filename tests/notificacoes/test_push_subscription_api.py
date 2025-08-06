import pytest
from rest_framework.test import APIClient

from notificacoes.models import PushSubscription

pytestmark = pytest.mark.django_db


def test_register_and_delete_push_subscription(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    url = "/api/notificacoes/push-subscription/"
    resp = client.post(url, {"token": "abc"})
    assert resp.status_code == 204
    assert PushSubscription.objects.filter(user=admin_user, token="abc").exists()
    resp = client.delete(url, {"token": "abc"})
    assert resp.status_code == 204
    assert not PushSubscription.objects.filter(token="abc").exists()
