import asyncio
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from channels.testing import WebsocketCommunicator

from chat.services import criar_canal
from Hubx.asgi import application


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.xfail(reason="Pending database issue with soft delete migrations")
def test_upload_and_notification(admin_user, coordenador_user, client):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    client.force_login(admin_user)
    up = SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")
    resp = client.post("/api/chat/upload/", {"file": up})
    assert resp.status_code == 200
    data = resp.json()

    async def inner():
        notif_comm = WebsocketCommunicator(application, "/ws/chat/notificacoes/")
        notif_comm.scope["user"] = coordenador_user
        connected, _ = await notif_comm.connect()
        assert connected
        chat_comm = WebsocketCommunicator(application, f"/ws/chat/{canal.id}/")
        chat_comm.scope["user"] = admin_user
        connected2, _ = await chat_comm.connect()
        assert connected2
        await chat_comm.send_json_to({"tipo": data["tipo"], "conteudo": data["url"]})
        await chat_comm.receive_json_from()
        notif = await notif_comm.receive_json_from()
        assert notif["tipo"] == data["tipo"]
        assert "canal_titulo" in notif
        await chat_comm.disconnect()
        await notif_comm.disconnect()

    asyncio.run(inner())

