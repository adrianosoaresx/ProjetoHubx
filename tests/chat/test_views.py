import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from chat.models import ChatChannel, ChatMessage, ChatParticipant

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
    data = {"titulo": "Nova"}
    resp = client.post(reverse("chat:nova_conversa"), data=data)
    assert resp.status_code == 302
    assert ChatChannel.objects.filter(titulo="Nova").exists()
    conv = ChatChannel.objects.get(titulo="Nova")
    assert conv.participants.filter(user=admin_user, is_owner=True).exists()


def test_conversation_detail_allows_post_message(client, admin_user, coordenador_user, media_root):
    conv = ChatChannel.objects.create(titulo="D", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)

    client.force_login(admin_user)
    resp = client.post(
        reverse("chat:conversation_detail", args=[conv.id]),
        {"tipo": "text", "conteudo": "hi"},
    )
    assert resp.status_code == 302
    assert ChatMessage.objects.filter(channel=conv, remetente=admin_user, conteudo="hi").exists()


def test_conversation_detail_denies_non_participant(client, admin_user):
    conv = ChatChannel.objects.create(titulo="D", contexto_tipo="privado")
    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_detail", args=[conv.id]))
    assert resp.status_code == 404


def test_conversation_detail_file_upload(client, admin_user, coordenador_user, media_root):
    conv = ChatChannel.objects.create(titulo="D", contexto_tipo="privado")
    ChatParticipant.objects.create(channel=conv, user=admin_user)
    ChatParticipant.objects.create(channel=conv, user=coordenador_user)
    client.force_login(admin_user)
    file = SimpleUploadedFile("f.txt", b"data")
    resp = client.post(
        reverse("chat:conversation_detail", args=[conv.id]),
        {"tipo": "file", "arquivo": file},
    )
    assert resp.status_code == 302
    msg = ChatMessage.objects.get(channel=conv)
    assert msg.arquivo.name.startswith("chat/arquivos/")
