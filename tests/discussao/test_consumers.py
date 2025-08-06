import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from discussao.factories import RespostaDiscussaoFactory, TopicoDiscussaoFactory
from Hubx.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def test_consumer_receives_new_response(admin_user):
    async def inner():
        topico = await database_sync_to_async(TopicoDiscussaoFactory.create)(autor=admin_user)
        communicator = WebsocketCommunicator(application, f"/ws/discussao/{topico.id}/")
        communicator.scope["user"] = admin_user
        connected, _ = await communicator.connect()
        assert connected
        await database_sync_to_async(RespostaDiscussaoFactory.create)(topico=topico, autor=admin_user, conteudo="ola")
        event = await communicator.receive_json_from()
        assert event["event"] == "nova_resposta"
        await communicator.disconnect()

    asyncio.run(inner())
