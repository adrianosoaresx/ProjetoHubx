from rest_framework.test import APIClient
from chat.models import ChatChannel, ChatParticipant, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()

def test_e2ee_message_stored_encrypted(admin_user):
    channel = ChatChannel.objects.create(contexto_tipo="privado", e2ee_habilitado=True)
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    client = APIClient()
    client.force_authenticate(admin_user)
    payload = {"tipo": "text", "conteudo": "ZW5j"}
    url = f"/api/chat/channels/{channel.pk}/messages/"
    resp = client.post(url, payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["conteudo_cifrado"] == "ZW5j"
    msg = ChatMessage.objects.get(id=data["id"])
    assert msg.conteudo == ""
    assert msg.conteudo_cifrado == "ZW5j"

def test_public_key_endpoints(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    resp = client.post("/api/chat/usuarios/chave-publica/", {"chave_publica": "abc"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["chave_publica"] == "abc"
    resp = client.get(f"/api/chat/usuarios/{admin_user.id}/chave-publica/")
    assert resp.status_code == 200
    assert resp.json()["chave_publica"] == "abc"
