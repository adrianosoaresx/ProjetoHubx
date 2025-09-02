from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import UserChatPreference

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_get_and_patch_preferences(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-preferences")

    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tema"] == "claro"
    assert UserChatPreference.objects.filter(user=admin_user).exists()

    resp = api_client.patch(url, {"tema": "escuro", "resumo_diario": True}, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tema"] == "escuro"
    assert data["resumo_diario"] is True
    pref = UserChatPreference.objects.get(user=admin_user)
    assert pref.tema == "escuro"
    assert pref.resumo_diario is True
