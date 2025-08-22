import pytest
import uuid
from django.urls import reverse

from chat.models import ChatChannel, ChatMessage, ChatModerationLog, ChatParticipant
from chat.services import criar_canal, enviar_mensagem

pytestmark = pytest.mark.django_db


def test_conversation_list_shows_user_conversations(client, admin_user, coordenador_user):
    conv1 = ChatChannel.objects.create(titulo="A", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv1, user=admin_user)
    ChatParticipant.objects.create(channel=conv1, user=coordenador_user)

    conv2 = ChatChannel.objects.create(titulo="B", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv2, user=coordenador_user)

    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_list"))
    assert resp.status_code == 200
    grupos = resp.context["grupos"]
    assert list(grupos["privado"]) == [conv1]
    assert list(grupos["organizacao"]) == []


def test_conversation_list_requires_login(client):
    resp = client.get(reverse("chat:conversation_list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


def test_nova_conversa_creates_conversation(client, admin_user, monkeypatch):
    from chat import views

    class DummyForm(views.NovaConversaForm):
        def __init__(self, *args, **kwargs):
            kwargs.pop("user", None)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(views, "NovaConversaForm", DummyForm)

    client.force_login(admin_user)
    data = {"titulo": "Nova", "contexto_tipo": "privado"}
    resp = client.post(reverse("chat:nova_conversa"), data=data)
    assert resp.status_code == 302
    assert ChatChannel.objects.filter(titulo="Nova").exists()
    conv = ChatChannel.objects.get(titulo="Nova")
    assert conv.participants.filter(user=admin_user, is_owner=True).exists()


def test_conversation_detail_denies_non_participant(client, admin_user):
    conv = ChatChannel.objects.create(titulo="D", contexto_tipo="privado")
    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_detail", args=[conv.id]))
    assert resp.status_code == 404


def test_historico_edicoes_view(client, admin_user):
    channel = ChatChannel.objects.create(titulo="H", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, conteudo="a")
    log = ChatModerationLog.objects.create(message=msg, action="edit", moderator=admin_user, previous_content="b")
    client.force_login(admin_user)
    resp = client.get(reverse("chat:historico_edicoes", args=[channel.id, msg.id]))
    assert resp.status_code == 200
    assert list(resp.context["logs"]) == [log]


def test_historico_edicoes_requires_admin(client, admin_user, coordenador_user):
    channel = ChatChannel.objects.create(titulo="H", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    ChatParticipant.objects.create(channel=channel, user=coordenador_user)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, conteudo="a")
    client.force_login(coordenador_user)
    resp = client.get(reverse("chat:historico_edicoes", args=[channel.id, msg.id]))
    assert resp.status_code == 403


def test_historico_edicoes_export_csv(client, admin_user):
    channel = ChatChannel.objects.create(titulo="H", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=channel, user=admin_user, is_admin=True)
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, conteudo="a")
    ChatModerationLog.objects.create(message=msg, action="edit", moderator=admin_user, previous_content="b")
    client.force_login(admin_user)
    resp = client.get(
        reverse("chat:historico_edicoes", args=[channel.id, msg.id]) + "?export=csv"
    )
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    assert "b" in resp.content.decode()


def test_modal_users_requires_login(client):
    resp = client.get(reverse("chat:modal_users"))
    assert resp.status_code == 302


def test_modal_users_lists_other_users(client, admin_user, coordenador_user):
    client.force_login(admin_user)
    resp = client.get(reverse("chat:modal_users"))
    assert resp.status_code == 200
    users = list(resp.context["users"])
    assert coordenador_user in users
    assert admin_user not in users


def test_modal_room_loads_messages(client, admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="",
        descricao="",
        participantes=[coordenador_user],
    )
    enviar_mensagem(canal, admin_user, "text", conteudo="olá")
    enviar_mensagem(canal, coordenador_user, "text", conteudo="oi")
    client.force_login(admin_user)
    user_uuid = uuid.UUID(int=coordenador_user.id)
    resp = client.get(reverse("chat:modal_room", args=[user_uuid]))
    assert resp.status_code == 200
    msgs = list(resp.context["messages"])
    assert [m.conteudo for m in msgs] == ["olá", "oi"]
