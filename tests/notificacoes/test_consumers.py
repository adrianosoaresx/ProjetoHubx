import asyncio

import pytest
from channels.testing import WebsocketCommunicator

from Hubx.asgi import application
from notificacoes.models import PushSubscription
from notificacoes.tasks import enviar_notificacao_async
from notificacoes.models import NotificationLog, NotificationTemplate, Canal

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def test_consumer_receives_message(admin_user, monkeypatch):
    async def inner():
        monkeypatch.setattr("notificacoes.tasks.send_push", lambda u, m: None)
        PushSubscription.objects.create(user=admin_user, token="t")
        communicator = WebsocketCommunicator(application, "/ws/notificacoes/")
        communicator.scope["user"] = admin_user
        connected, _ = await communicator.connect()
        assert connected
        template = NotificationTemplate.objects.create(codigo="t", assunto="A", corpo="B", canal=Canal.PUSH)
        log = NotificationLog.objects.create(user=admin_user, template=template, canal=Canal.PUSH)
        await enviar_notificacao_async("A", "B", str(log.id))
        response = await communicator.receive_json_from()
        assert response["mensagem"] == "B"
        await communicator.disconnect()
    asyncio.run(inner())


def test_consumer_rejects_anonymous():
    async def inner():
        communicator = WebsocketCommunicator(application, "/ws/notificacoes/")
        connected, _ = await communicator.connect()
        assert not connected
    asyncio.run(inner())
