from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import ChatAttachment, ChatChannel, ChatMessage, ChatModerationLog, ChatParticipant
from chat.tasks import aplicar_politica_retencao

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_config_retencao_updates_value(api_client: APIClient, admin_user) -> None:
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-config-retencao", args=[channel.pk])
    resp = api_client.patch(url, {"retencao_dias": 30}, format="json")
    assert resp.status_code == 200
    channel.refresh_from_db()
    assert channel.retencao_dias == 30


def test_config_retencao_requires_admin(api_client: APIClient, admin_user, coordenador_user) -> None:
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    api_client.force_authenticate(coordenador_user)
    url = reverse("chat_api:chat-channel-config-retencao", args=[channel.pk])
    resp = api_client.patch(url, {"retencao_dias": 10}, format="json")
    assert resp.status_code == 403


def test_config_retencao_validation(api_client: APIClient, admin_user) -> None:
    channel = ChatChannel.objects.create(contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-channel-config-retencao", args=[channel.pk])
    resp = api_client.patch(url, {"retencao_dias": 400}, format="json")
    assert resp.status_code == 400


def test_aplicar_politica_retencao_remove_mensagens(admin_user) -> None:
    channel = ChatChannel.objects.create(contexto_tipo="privado", retencao_dias=30)
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    old_time = timezone.now() - timedelta(days=40)
    old_msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="old")
    ChatMessage.objects.filter(pk=old_msg.pk).update(created=old_time)
    att = ChatAttachment.objects.create(mensagem=old_msg, arquivo=SimpleUploadedFile("a.txt", b"a"))
    new_msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="new")
    aplicar_politica_retencao()
    assert not ChatMessage.objects.filter(id=old_msg.id).exists()
    assert ChatMessage.objects.filter(id=new_msg.id).exists()
    assert not ChatAttachment.objects.filter(id=att.id).exists()
    assert ChatModerationLog.objects.filter(message_id=old_msg.id, action="retencao").exists()
