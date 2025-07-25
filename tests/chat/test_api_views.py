import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatConversation, ChatMessage, ChatParticipant

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_pin_message(api_client: APIClient, admin_user, coordenador_user):
    conv = ChatConversation.objects.create(titulo="t", slug="t", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(conversation=conv, user=coordenador_user)
    msg = ChatMessage.objects.create(conversation=conv, sender=coordenador_user, tipo="text", conteudo="hi")

    api_client.force_authenticate(admin_user)
    url = reverse("chat:mensagem-pin", args=[msg.pk])
    resp = api_client.post(url)
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.pinned_at is not None


def test_react_message(api_client: APIClient, admin_user):
    conv = ChatConversation.objects.create(titulo="r", slug="r", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv, user=admin_user)
    msg = ChatMessage.objects.create(conversation=conv, sender=admin_user, tipo="text", conteudo="hi")

    api_client.force_authenticate(admin_user)
    url = reverse("chat:mensagem-react", args=[msg.pk])
    resp = api_client.post(url, {"emoji": "👍"})
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.reactions.get("👍") == 1
