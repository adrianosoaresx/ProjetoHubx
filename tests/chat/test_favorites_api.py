import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatChannel, ChatMessage, ChatParticipant, ChatFavorite

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_favorite_message_flow(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    msg = ChatMessage.objects.create(
        channel=channel,
        remetente=coordenador_user,
        tipo="text",
        conteudo="ola",
    )
    api_client.force_authenticate(admin_user)
    fav_url = f"/api/chat/channels/{channel.id}/messages/{msg.id}/favorite/"
    resp = api_client.post(fav_url)
    assert resp.status_code == 201
    assert ChatFavorite.objects.filter(user=admin_user, message=msg).exists()

    list_url = reverse("chat_api:chat-favorite-list")
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert str(channel.id) in results
    assert results[str(channel.id)][0]["id"] == str(msg.id)

    resp = api_client.delete(fav_url)
    assert resp.status_code == 204
    assert not ChatFavorite.objects.filter(user=admin_user, message=msg).exists()
