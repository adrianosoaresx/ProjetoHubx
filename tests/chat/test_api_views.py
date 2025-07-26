import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatConversation, ChatMessage, ChatParticipant

User = get_user_model()

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


def test_flag_message_hides(api_client: APIClient, admin_user):
    conv = ChatConversation.objects.create(titulo="f", slug="f", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv, user=admin_user)
    other1 = User.objects.create_user(email="o1@x.com", username="o1", password="x")
    other2 = User.objects.create_user(email="o2@x.com", username="o2", password="x")
    ChatParticipant.objects.create(conversation=conv, user=other1)
    ChatParticipant.objects.create(conversation=conv, user=other2)
    msg = ChatMessage.objects.create(conversation=conv, sender=admin_user, tipo="text", conteudo="hi")

    url = reverse("chat:mensagem-flag", args=[msg.pk])
    api_client.force_authenticate(admin_user)
    api_client.post(url)
    api_client.force_authenticate(other1)
    api_client.post(url)
    api_client.force_authenticate(other2)
    api_client.post(url)
    msg.refresh_from_db()
    assert msg.hidden_at is not None


def test_export_channel(api_client: APIClient, admin_user):
    conv = ChatConversation.objects.create(titulo="e", slug="e", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv, user=admin_user, is_admin=True)
    ChatMessage.objects.create(conversation=conv, sender=admin_user, conteudo="hi")
    api_client.force_authenticate(admin_user)
    url = reverse("chat:canal_exportar", args=[conv.pk]) + "?formato=json"
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()["url"].endswith(".json")
