from django.contrib.auth import get_user_model
from django.test import TestCase

from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .forms import NovaMensagemForm
from .models import ChatConversation, ChatMessage, ChatNotification, ChatParticipant

User = get_user_model()


class ChatBasicsTests(TestCase):
    def setUp(self) -> None:
        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo = Nucleo.objects.create(nome="Nuc", organizacao=org)
        self.user1 = User.objects.create_user(
            email="u1@example.com",
            username="user1",
            password="pass",
            nucleo=self.nucleo,
        )
        self.user2 = User.objects.create_user(
            email="u2@example.com",
            username="user2",
            password="pass",
            nucleo=self.nucleo,
        )
        self.client.force_login(self.user1)

    def test_create_direct_conversation(self):
        conv = ChatConversation.objects.create(titulo="Direta", slug="d1", tipo_conversa="direta")
        ChatParticipant.objects.create(conversation=conv, user=self.user1, is_owner=True)
        ChatParticipant.objects.create(conversation=conv, user=self.user2)
        self.assertEqual(conv.participants.count(), 2)

    def test_message_form_requires_content_or_file(self):
        form = NovaMensagemForm(data={}, files={})
        self.assertFalse(form.is_valid())

    def test_send_message_marks_read_by_sender(self):
        conv = ChatConversation.objects.create(
            titulo="Direta",
            slug="d2",
            tipo_conversa="direta",
            organizacao=self.nucleo.organizacao,
        )
        ChatParticipant.objects.create(conversation=conv, user=self.user1, is_owner=True)
        ChatParticipant.objects.create(conversation=conv, user=self.user2)
        msg = ChatMessage.objects.create(conversation=conv, sender=self.user1, conteudo="hello")
        self.assertEqual(msg.organizacao, conv.organizacao)
        msg.lido_por.add(self.user1)
        self.assertIn(self.user1, msg.lido_por.all())
        self.assertFalse(ChatNotification.objects.exists())
