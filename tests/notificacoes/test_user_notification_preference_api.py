import pytest
from rest_framework.test import APIClient

from notificacoes.models import UserNotificationPreference

pytestmark = pytest.mark.django_db


def test_create_preferences(admin_user):
    UserNotificationPreference.objects.filter(user=admin_user).delete()
    client = APIClient()
    client.force_authenticate(admin_user)
    url = "/api/notificacoes/preferences/"
    data = {"email": False, "push": True, "whatsapp": False}
    resp = client.post(url, data)
    assert resp.status_code == 201
    prefs = UserNotificationPreference.objects.get(user=admin_user)
    assert prefs.email is False
    assert prefs.push is True
    assert prefs.whatsapp is False


def test_update_preferences(admin_user):
    prefs = UserNotificationPreference.objects.get(user=admin_user)
    client = APIClient()
    client.force_authenticate(admin_user)
    url = f"/api/notificacoes/preferences/{prefs.id}/"
    resp = client.patch(url, {"email": False}, format="json")
    assert resp.status_code == 200
    prefs.refresh_from_db()
    assert prefs.email is False
