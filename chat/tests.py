import asyncio

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from Hubx.asgi import application
from nucleos.models import Nucleo
from organizacoes.models import Organizacao

from .models import Mensagem, Notificacao

User = get_user_model()


class ChatViewTests(TestCase):
    def setUp(self):
        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo = Nucleo.objects.create(nome="Nuc", organizacao=org)
        self.user1 = User.objects.create_user(
            "user1", password="pass", nucleo=self.nucleo
        )
        self.user2 = User.objects.create_user(
            "user2", password="pass", nucleo=self.nucleo
        )
        Mensagem.objects.create(
            nucleo=self.nucleo,
            remetente=self.user1,
            destinatario=self.user2,
            tipo="text",
            conteudo="hello",
        )
        Mensagem.objects.create(
            nucleo=self.nucleo,
            remetente=self.user2,
            destinatario=self.user1,
            tipo="text",
            conteudo="hi",
        )
        self.client.force_login(self.user1)

    def test_conversation_shows_previous_messages(self):
        url = reverse("chat:modal_room", args=[self.user2.id])
        response = self.client.get(url)
        self.assertContains(response, "hello")
        self.assertContains(response, "hi")

    def test_messages_history_endpoint_returns_json(self):
        url = reverse("chat:messages_history", args=[self.user2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 2)


from unittest import skip


@skip("WebSocket communication unsupported in this environment")
class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")
        self.nucleo = Nucleo.objects.create(nome="Nuc", organizacao=org)
        self.sender = User.objects.create_user(
            "sender", password="pass", nucleo=self.nucleo
        )
        self.receiver = User.objects.create_user(
            "receiver", password="pass", nucleo=self.nucleo
        )

    async def _communicate(self):
        comm_sender = WebsocketCommunicator(
            application, f"/ws/chat/{self.receiver.id}/"
        )
        comm_sender.scope["user"] = self.sender
        connected, _ = await comm_sender.connect()
        assert connected

        comm_receiver = WebsocketCommunicator(
            application, f"/ws/chat/{self.sender.id}/"
        )
        comm_receiver.scope["user"] = self.receiver
        connected, _ = await comm_receiver.connect()
        assert connected

        await comm_sender.send_json_to({"tipo": "text", "conteudo": "ping"})
        await asyncio.sleep(0.1)
        data = await comm_receiver.receive_json_from(timeout=5)
        self.assertEqual(data["conteudo"], "ping")
        await comm_sender.disconnect()
        await comm_receiver.disconnect()

    def test_websocket_message_creates_notification(self):
        asyncio.get_event_loop().run_until_complete(self._communicate())
        self.assertTrue(Mensagem.objects.filter(conteudo="ping").exists())
        self.assertTrue(
            Notificacao.objects.filter(
                usuario=self.receiver, mensagem__conteudo="ping"
            ).exists()
        )
