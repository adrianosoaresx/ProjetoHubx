import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from chat.models import ChatConversation, ChatMessage, ChatMessageFlag, ChatParticipant

pytestmark = pytest.mark.django_db


def test_review_flagged_message(admin_user):
    client = APIClient()
    conv = ChatConversation.objects.create(titulo="c", slug="c", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv, user=admin_user)
    msg = ChatMessage.objects.create(conversation=conv, sender=admin_user, conteudo="oi")
    ChatMessageFlag.objects.create(message=msg, user=admin_user)
    client.force_authenticate(admin_user)
    url = reverse("chat:mensagem-revisar", args=[msg.pk])
    resp = client.post(url, {"acao": "aprovar"})
    assert resp.status_code == 200
    msg.refresh_from_db()
    assert msg.hidden_at is None
