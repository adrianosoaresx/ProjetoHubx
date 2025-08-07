from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatChannel, ChatChannelCategory, ChatParticipant

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_category_crud_permissions(api_client: APIClient, admin_user, associado_user):
    url = reverse("chat_api:chat-categoria-list")
    api_client.force_authenticate(associado_user)
    resp = api_client.post(url, {"nome": "Geral"})
    assert resp.status_code == 403

    api_client.force_authenticate(admin_user)
    resp = api_client.post(url, {"nome": "Geral"})
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    detail = reverse("chat_api:chat-categoria-detail", args=[cat_id])
    api_client.force_authenticate(associado_user)
    resp = api_client.patch(detail, {"descricao": "x"})
    assert resp.status_code == 403

    api_client.force_authenticate(admin_user)
    resp = api_client.patch(detail, {"descricao": "x"})
    assert resp.status_code == 200


def test_category_list_filter(api_client: APIClient, admin_user):
    ChatChannelCategory.objects.create(nome="Suporte")
    ChatChannelCategory.objects.create(nome="Financeiro")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-categoria-list")
    resp = api_client.get(url, {"nome": "sup"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Suporte"


def test_channel_list_filter_by_categoria(api_client: APIClient, admin_user):
    cat1 = ChatChannelCategory.objects.create(nome="Cat1")
    cat2 = ChatChannelCategory.objects.create(nome="Cat2")
    c1 = ChatChannel.objects.create(contexto_tipo="privado", categoria=cat1)
    c2 = ChatChannel.objects.create(contexto_tipo="privado", categoria=cat2)
    ChatParticipant.objects.create(channel=c1, user=admin_user)
    ChatParticipant.objects.create(channel=c2, user=admin_user)
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-list")
    resp = api_client.get(url, {"categoria": cat1.id})
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert str(c1.id) in ids
    assert str(c2.id) not in ids
