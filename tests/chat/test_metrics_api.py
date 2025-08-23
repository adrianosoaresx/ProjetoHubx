import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import (
    ChatAttachment,
    ChatChannel,
    ChatChannelCategory,
    ChatMessage,
    ChatMessageFlag,
    ChatMessageReaction,
    ChatParticipant,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_metrics_endpoint_returns_counts(api_client: APIClient, admin_user):
    cat = ChatChannelCategory.objects.create(nome="Cat")
    channel = ChatChannel.objects.create(contexto_tipo="privado", categoria=cat)
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    msg1 = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text", conteudo="a")
    msg2 = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="image",
        conteudo="b",
        hidden_at=timezone.now(),
    )
    ChatMessageReaction.objects.create(message=msg1, user=admin_user, emoji="👍")
    ChatMessageFlag.objects.create(message=msg1, user=admin_user)
    file1 = SimpleUploadedFile("d.txt", b"1")
    ChatAttachment.objects.create(
        mensagem=msg1,
        usuario=admin_user,
        arquivo=file1,
        mime_type="text/plain",
        tamanho=1,
    )
    api_client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-metrics")
    resp = api_client.get(url, {"categoria": cat.id})
    assert resp.status_code == 200
    data = resp.json()["resultados"][0]
    assert data["total_mensagens"] == 2
    assert data["mensagens_por_tipo"]["text"] == 1
    assert data["mensagens_por_tipo"]["image"] == 1
    assert data["total_reacoes"] == 1
    assert data["mensagens_sinalizadas"] == 1
    assert data["mensagens_ocultadas"] == 1
    assert data["total_anexos"] == 1
