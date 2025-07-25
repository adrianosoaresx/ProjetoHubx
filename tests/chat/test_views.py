import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from chat.models import ChatConversation, ChatMessage, ChatParticipant

pytestmark = pytest.mark.django_db


def test_conversation_list_shows_user_conversations(client, admin_user, coordenador_user):
    conv1 = ChatConversation.objects.create(titulo="A", slug="a", tipo_conversa="direta")
    ChatParticipant.objects.create(conversation=conv1, user=admin_user)
    ChatParticipant.objects.create(conversation=conv1, user=coordenador_user)

    conv2 = ChatConversation.objects.create(titulo="B", slug="b", tipo_conversa="grupo")
    ChatParticipant.objects.create(conversation=conv2, user=coordenador_user)

    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_list"))
    assert resp.status_code == 200
    grupos = resp.context["grupos"]
    assert list(grupos["direta"]) == [conv1]
    assert list(grupos["grupo"]) == []


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
    data = {"titulo": "Nova", "slug": "nova", "tipo_conversa": "grupo"}
    resp = client.post(reverse("chat:nova_conversa"), data=data)
    assert resp.status_code == 302
    assert ChatConversation.objects.filter(slug="nova").exists()
    conv = ChatConversation.objects.get(slug="nova")
    assert conv.participants.filter(user=admin_user, is_owner=True).exists()


def test_conversation_detail_allows_post_message(client, admin_user, coordenador_user, media_root):
    conv = ChatConversation.objects.create(titulo="D", slug="d", tipo_conversa="direta")
    ChatParticipant.objects.create(conversation=conv, user=admin_user)
    ChatParticipant.objects.create(conversation=conv, user=coordenador_user)

    client.force_login(admin_user)
    resp = client.post(
        reverse("chat:conversation_detail", args=[conv.slug]),
        {"tipo": "text", "conteudo": "hi"},
    )
    assert resp.status_code == 302
    assert ChatMessage.objects.filter(conversation=conv, sender=admin_user, conteudo="hi").exists()


def test_conversation_detail_denies_non_participant(client, admin_user):
    conv = ChatConversation.objects.create(titulo="D", slug="d2", tipo_conversa="direta")
    client.force_login(admin_user)
    resp = client.get(reverse("chat:conversation_detail", args=[conv.slug]))
    assert resp.status_code == 404


def test_conversation_detail_file_upload(client, admin_user, coordenador_user, media_root):
    conv = ChatConversation.objects.create(titulo="D", slug="df", tipo_conversa="direta")
    ChatParticipant.objects.create(conversation=conv, user=admin_user)
    ChatParticipant.objects.create(conversation=conv, user=coordenador_user)
    client.force_login(admin_user)
    file = SimpleUploadedFile("f.txt", b"data")
    resp = client.post(
        reverse("chat:conversation_detail", args=[conv.slug]),
        {"tipo": "file", "arquivo": file},
    )
    assert resp.status_code == 302
    msg = ChatMessage.objects.get(conversation=conv)
    assert msg.arquivo.name.startswith("chat/arquivos/")
