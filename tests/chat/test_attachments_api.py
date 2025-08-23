import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatAttachment, ChatChannel, ChatMessage, ChatParticipant


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_list_attachments_filters_infected(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="file")
    file1 = SimpleUploadedFile("a.txt", b"1")
    att1 = ChatAttachment.objects.create(
        mensagem=msg,
        usuario=admin_user,
        arquivo=file1,
        mime_type="text/plain",
        tamanho=1,
    )
    file2 = SimpleUploadedFile("b.txt", b"1")
    ChatAttachment.objects.create(
        mensagem=msg,
        usuario=admin_user,
        arquivo=file2,
        mime_type="text/plain",
        tamanho=1,
        infected=True,
    )
    api_client.force_authenticate(coordenador_user)
    url = reverse("chat_api:chat-channel-attachments", args=[channel.id])
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(att1.id)

    api_client.force_authenticate(admin_user)
    resp = api_client.get(url)
    ids = [a["id"] for a in resp.json()]
    assert str(att1.id) in ids


def test_delete_attachment_requires_admin(api_client: APIClient, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="file")
    file1 = SimpleUploadedFile("c.txt", b"1")
    att = ChatAttachment.objects.create(
        mensagem=msg,
        usuario=admin_user,
        arquivo=file1,
        mime_type="text/plain",
        tamanho=1,
    )
    url = reverse("chat_api:chat-attachment-detail", args=[att.id])
    api_client.force_authenticate(coordenador_user)
    resp = api_client.delete(url)
    assert resp.status_code == 403

    api_client.force_authenticate(admin_user)
    resp = api_client.delete(url)
    assert resp.status_code == 204
    assert not ChatAttachment.objects.filter(id=att.id).exists()

