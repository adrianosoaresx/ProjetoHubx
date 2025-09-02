import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.utils import timezone

from discussao.models import TopicoDiscussao
from Hubx.asgi import application
from nucleos.models import ParticipacaoNucleo

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def in_memory_channel_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def test_discussion_consumer_blocks_suspended_member(categoria, nucleo, coordenador_user):
    async def inner():
        part = await database_sync_to_async(ParticipacaoNucleo.objects.create)(
            user=coordenador_user, nucleo=nucleo, status="ativo"
        )
        topico = await database_sync_to_async(TopicoDiscussao.objects.create)(
            categoria=categoria,
            titulo="Topico",
            conteudo="x",
            autor=coordenador_user,
            publico_alvo=0,
            nucleo=nucleo,
        )
        part.status_suspensao = True
        part.data_suspensao = timezone.now()
        await database_sync_to_async(part.save)()
        communicator = WebsocketCommunicator(application, f"/ws/discussao/{topico.id}/")
        communicator.scope["user"] = coordenador_user
        connected, _ = await communicator.connect()
        assert connected is False
        await communicator.disconnect()

    asyncio.run(inner())
