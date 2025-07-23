import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from chat.models import ChatConversation, ChatMessage, ChatNotification, ChatParticipant

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "tipo,rel_field",
    [
        ("direta", None),
        ("grupo", None),
        ("organizacao", "organizacao"),
        ("nucleo", "nucleo"),
        ("evento", "evento"),
    ],
)
def test_chat_conversation_creation(tipo, rel_field, organizacao, nucleo, evento):
    data = {"titulo": "Conversa", "slug": f"slug-{tipo}", "tipo_conversa": tipo}
    if rel_field == "organizacao":
        data["organizacao"] = organizacao
    if rel_field == "nucleo":
        data["nucleo"] = nucleo
    if rel_field == "evento":
        data["evento"] = evento
    conv = ChatConversation.objects.create(**data)
    assert conv.tipo_conversa == tipo
    if rel_field:
        assert getattr(conv, rel_field) is not None
    else:
        assert conv.organizacao is None and conv.nucleo is None and conv.evento is None


def test_chat_conversation_slug_unique(organizacao):
    ChatConversation.objects.create(titulo="C1", slug="s", tipo_conversa="grupo")
    with pytest.raises(IntegrityError):
        ChatConversation.objects.create(titulo="C2", slug="s", tipo_conversa="grupo")


def test_chat_participant_unique(conversation, admin_user):
    ChatParticipant.objects.create(conversation=conversation, user=admin_user)
    with pytest.raises(IntegrityError):
        ChatParticipant.objects.create(conversation=conversation, user=admin_user)


def test_chat_participant_flags(conversation, admin_user, coordenador_user):
    owner = ChatParticipant.objects.create(
        conversation=conversation,
        user=admin_user,
        is_owner=True,
    )
    admin = ChatParticipant.objects.create(
        conversation=conversation,
        user=coordenador_user,
        is_admin=True,
    )
    assert owner.is_owner is True and owner.is_admin is False
    assert admin.is_admin is True and admin.is_owner is False


def test_chat_message_creation(media_root, conversation, admin_user):
    msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=admin_user,
        conteudo="hello",
    )
    assert msg.conversation == conversation
    assert msg.sender == admin_user
    msg.lido_por.add(admin_user)
    assert admin_user in msg.lido_por.all()


@pytest.mark.xfail(reason="Arquivo não é removido ao deletar a mensagem")
def test_chat_message_file_handling(media_root, conversation, admin_user):
    file = SimpleUploadedFile("file.txt", b"data")
    msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=admin_user,
        arquivo=file,
    )
    assert msg.arquivo.name.startswith("chat/arquivos/")
    path = msg.arquivo.path
    assert os.path.exists(path)
    msg.delete()
    assert not os.path.exists(path)


def test_chat_notification_basic(conversation, admin_user):
    msg = ChatMessage.objects.create(
        conversation=conversation,
        sender=admin_user,
        conteudo="oi",
    )
    notif = ChatNotification.objects.create(user=admin_user, mensagem=msg)
    assert notif.lido is False
    notif.lido = True
    notif.save()
    notif.refresh_from_db()
    assert notif.lido is True


# Helpers
@pytest.fixture
def conversation(organizacao):
    return ChatConversation.objects.create(
        titulo="Conv",
        slug="conv",
        tipo_conversa="grupo",
        organizacao=organizacao,
    )
