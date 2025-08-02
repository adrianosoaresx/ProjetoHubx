from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatChannel, ChatMessage, ChatParticipant

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_list_channels_returns_only_participated(api_client: APIClient, admin_user, coordenador_user):
    c1 = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=c1, user=admin_user)
    c2 = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=c2, user=coordenador_user)
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-list")
    resp = api_client.get(url)
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert str(c1.id) in ids
    assert str(c2.id) not in ids


def test_create_channel_requires_permission(api_client: APIClient, associado_user):
    api_client.force_authenticate(associado_user)
    url = reverse("chat_api:chat-channel-list")
    resp = api_client.post(url, {"contexto_tipo": "privado", "titulo": "x"})
    assert resp.status_code == 201
    resp2 = api_client.post(
        url,
        {"contexto_tipo": "nucleo", "contexto_id": uuid.uuid4()},
    )
    assert resp2.status_code == 403


def test_add_and_remove_participant(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    api_client.force_authenticate(admin_user)
    add_url = reverse("chat_api:chat-channel-add-participant", args=[channel.pk])
    resp = api_client.post(add_url, {"usuarios": [coordenador_user.id]})
    assert resp.status_code == 200
    assert ChatParticipant.objects.filter(channel=channel, user=coordenador_user).exists()
    remove_url = reverse("chat_api:chat-channel-remove-participant", args=[channel.pk])
    resp = api_client.post(remove_url, {"usuarios": [coordenador_user.id]})
    assert resp.status_code == 200
    assert not ChatParticipant.objects.filter(channel=channel, user=coordenador_user).exists()


def test_send_and_list_messages(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    api_client.force_authenticate(admin_user)
    list_url = reverse("chat_api:chat-messages-list", kwargs={"channel_pk": channel.pk})
    resp = api_client.post(list_url, {"tipo": "text", "conteudo": "hi"})
    assert resp.status_code == 201
    msg = ChatMessage.objects.first()
    resp = api_client.get(list_url, {"desde": msg.timestamp.isoformat()})
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_messages_permission_denied_for_non_participant(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    api_client.force_authenticate(coordenador_user)
    url = reverse("chat_api:chat-messages-list", kwargs={"channel_pk": channel.pk})
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_pin_message(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=coordenador_user, tipo="text", conteudo="hi")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-messages-pin", kwargs={"channel_pk": conv.pk, "pk": msg.pk})
    resp = api_client.post(url)
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.pinned_at is not None


def test_react_message(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-messages-react", kwargs={"channel_pk": conv.pk, "pk": msg.pk})
    resp = api_client.post(url, {"emoji": "👍"})
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.reactions.get("👍") == 1


def test_flag_message_hides(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    other1 = User.objects.create_user(email="o1@x.com", username="o1", password="x")
    other2 = User.objects.create_user(email="o2@x.com", username="o2", password="x")
    ChatParticipant.objects.create(channel=conv, user=other1)
    ChatParticipant.objects.create(channel=conv, user=other2)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, tipo="text", conteudo="hi")
    url = reverse("chat_api:chat-messages-flag", kwargs={"channel_pk": conv.pk, "pk": msg.pk})
    api_client.force_authenticate(admin_user)
    api_client.post(url)
    api_client.force_authenticate(other1)
    api_client.post(url)
    api_client.force_authenticate(other2)
    api_client.post(url)
    msg.refresh_from_db()
    assert msg.hidden_at is not None


def test_export_channel(api_client: APIClient, admin_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user, is_admin=True)
    ChatMessage.objects.create(channel=conv, remetente=admin_user, conteudo="hi")
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:conversa_exportar", args=[conv.id]) + "?formato=json"
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()["url"].endswith(".json")


def test_export_requires_permission(api_client: APIClient, associado_user):
    conv = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=associado_user)
    api_client.force_authenticate(associado_user)
    url = reverse("chat_api:conversa_exportar", args=[conv.id])
    resp = api_client.get(url)
    assert resp.status_code == 403
