import pytest
from rest_framework.test import APIClient

from notificacoes.models import PushSubscription

pytestmark = pytest.mark.django_db


def test_crud_push_subscription(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    url = "/api/notificacoes/push/subscriptions/"
    data = {
        "device_id": "dev1",
        "endpoint": "https://example.com/ep",
        "p256dh": "p",
        "auth": "a",
    }
    resp = client.post(url, data)
    assert resp.status_code in {200, 201}
    sub_id = resp.data["id"]
    assert PushSubscription.objects.filter(id=sub_id, active=True).exists()

    resp = client.get(url)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.delete(f"{url}{sub_id}/")
    assert resp.status_code == 204
    assert PushSubscription.objects.filter(id=sub_id, active=False).exists()
