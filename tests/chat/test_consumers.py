import os

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from chat.models import ChatMessage
from chat.services import criar_canal
from Hubx.asgi import application

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@pytest.mark.asyncio
async def test_consumer_connect_send_message_and_reaction(admin_user, coordenador_user):
    canal = await database_sync_to_async(criar_canal)(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    communicator = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
    communicator.scope["user"] = admin_user
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"tipo": "text", "conteudo": "olá"})
    response = await communicator.receive_json_from()
    assert response["conteudo"] == "olá"
    msg = await database_sync_to_async(ChatMessage.objects.get)(pk=response["id"])
    await communicator.send_json_to({"tipo": "reaction", "mensagem_id": str(msg.id), "emoji": "👍"})
    response2 = await communicator.receive_json_from()
    assert response2["reactions"]["👍"] == 1
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_consumer_rejects_non_participant(admin_user, associado_user):
    canal = await database_sync_to_async(criar_canal)(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[],
    )
    communicator = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
    communicator.scope["user"] = associado_user
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()
