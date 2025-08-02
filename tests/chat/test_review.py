import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatChannel, ChatMessage, ChatMessageFlag, ChatParticipant

pytestmark = pytest.mark.django_db


def test_review_flagged_message(admin_user):
    client = APIClient()
    conv = ChatChannel.objects.create(titulo="c", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=admin_user, conteudo="oi")
    ChatMessageFlag.objects.create(message=msg, user=admin_user)
    client.force_authenticate(admin_user)
    url = reverse("chat_api:chat-moderacao-approve", args=[msg.id])
    resp = client.post(url)
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.hidden_at is None


def test_moderate_requires_permission(associado_user):
    client = APIClient()
    conv = ChatChannel.objects.create(titulo="c2", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=associado_user)
    msg = ChatMessage.objects.create(channel=conv, remetente=associado_user, conteudo="oi")
    ChatMessageFlag.objects.create(message=msg, user=associado_user)
    client.force_authenticate(associado_user)
    url = reverse("chat_api:chat-moderacao-approve", args=[msg.id])
    resp = client.post(url)
    assert resp.status_code == 403
