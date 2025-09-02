import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from chat.models import ChatChannel, ChatMessage, ChatParticipant

pytestmark = pytest.mark.django_db


def _create_channel(user):
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=user)
    return channel


def test_message_partial_renders_media(client, admin_user, media_root):
    channel = _create_channel(admin_user)
    client.force_login(admin_user)
    msg_text = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="oi")
    resp_text = client.get(reverse("chat:message_partial", args=[msg_text.id]))
    html = resp_text.content.decode()
    assert "oi" in html

    img = SimpleUploadedFile("i.png", b"data", content_type="image/png")
    msg_img = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="image", arquivo=img)
    resp_img = client.get(reverse("chat:message_partial", args=[msg_img.id]))
    assert "<img" in resp_img.content.decode()

    vid = SimpleUploadedFile("v.mp4", b"data", content_type="video/mp4")
    msg_vid = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="video", arquivo=vid)
    resp_vid = client.get(reverse("chat:message_partial", args=[msg_vid.id]))
    assert "<video" in resp_vid.content.decode()

    f = SimpleUploadedFile("f.txt", b"data")
    msg_file = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="file", arquivo=f)
    resp_file = client.get(reverse("chat:message_partial", args=[msg_file.id]))
    assert "<a href" in resp_file.content.decode()


def test_conversation_detail_has_aria_labels(client, admin_user):
    channel = _create_channel(admin_user)
    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_detail", args=[channel.id]))
    html = resp.content.decode()
    assert 'aria-label="Enviar mensagem"' in html
