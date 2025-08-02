import os

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


import asyncio


def test_consumer_connect_send_message_and_reaction(admin_user, coordenador_user):
    async def inner():
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

    asyncio.run(inner())


def test_consumer_rejects_non_participant(admin_user, associado_user):
    async def inner():
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

    asyncio.run(inner())


def test_flag_via_websocket_hides_message(admin_user):
    from django.contrib.auth import get_user_model

    async def inner():
        User = get_user_model()
        u2 = User.objects.create_user(username="u2", email="u2@x.com", password="x")
        u3 = User.objects.create_user(username="u3", email="u3@x.com", password="x")
        u4 = User.objects.create_user(username="u4", email="u4@x.com", password="x")
        canal = await database_sync_to_async(criar_canal)(
            criador=admin_user,
            contexto_tipo="privado",
            contexto_id=None,
            titulo="Privado",
            descricao="",
            participantes=[u2, u3, u4],
        )
        comm_sender = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
        comm_sender.scope["user"] = admin_user
        connected, _ = await comm_sender.connect()
        assert connected
        await comm_sender.send_json_to({"tipo": "text", "conteudo": "oi"})
        msg_event = await comm_sender.receive_json_from()
        msg_id = msg_event["id"]
        comm2 = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
        comm2.scope["user"] = u2
        await comm2.connect()
        comm3 = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
        comm3.scope["user"] = u3
        await comm3.connect()
        comm4 = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
        comm4.scope["user"] = u4
        await comm4.connect()
        await comm2.send_json_to({"tipo": "flag", "mensagem_id": msg_id})
        await comm3.send_json_to({"tipo": "flag", "mensagem_id": msg_id})
        await comm4.send_json_to({"tipo": "flag", "mensagem_id": msg_id})
        update = await comm_sender.receive_json_from()
        assert update["hidden_at"] is not None
        await comm_sender.disconnect()
        await comm2.disconnect()
        await comm3.disconnect()
        await comm4.disconnect()

    asyncio.run(inner())
