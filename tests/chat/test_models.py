import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from chat.models import ChatChannel, ChatMessage, ChatNotification, ChatParticipant

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("tipo", ["privado", "organizacao", "nucleo", "evento"])
def test_chat_channel_creation(tipo, organizacao, nucleo, evento):
    data = {"titulo": "Conversa", "contexto_tipo": tipo}
    if tipo == "organizacao":
        data["contexto_id"] = organizacao.id
    elif tipo == "nucleo":
        data["contexto_id"] = nucleo.id
    elif tipo == "evento":
        data["contexto_id"] = evento.id
    channel = ChatChannel.objects.create(**data)
    assert channel.contexto_tipo == tipo
    if tipo == "privado":
        assert channel.contexto_id is None
    else:
        assert channel.contexto_id is not None


def test_chat_participant_unique(channel, admin_user):
    ChatParticipant.objects.create(channel=channel, user=admin_user)
    with pytest.raises(IntegrityError):
        ChatParticipant.objects.create(channel=channel, user=admin_user)


def test_chat_participant_flags(channel, admin_user, coordenador_user):
    owner = ChatParticipant.objects.create(
        channel=channel,
        user=admin_user,
        is_owner=True,
    )
    admin = ChatParticipant.objects.create(
        channel=channel,
        user=coordenador_user,
        is_admin=True,
    )
    assert owner.is_owner is True and owner.is_admin is False
    assert admin.is_admin is True and admin.is_owner is False


def test_chat_message_creation(media_root, channel, admin_user):
    msg = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="text",
        conteudo="hello",
    )
    assert msg.channel == channel
    assert msg.remetente == admin_user
    msg.lido_por.add(admin_user)
    assert admin_user in msg.lido_por.all()
    assert msg.created_at and msg.updated_at


def test_soft_delete_models(channel, admin_user):
    msg = ChatMessage.objects.create(channel=channel, remetente=admin_user, tipo="text")
    channel.delete()
    msg.delete()
    assert channel.deleted and channel.deleted_at is not None
    assert msg.deleted and msg.deleted_at is not None
    assert ChatChannel.objects.filter(pk=channel.pk).count() == 0
    assert ChatChannel.all_objects.filter(pk=channel.pk).exists()
    assert ChatMessage.objects.filter(pk=msg.pk).count() == 0
    assert ChatMessage.all_objects.filter(pk=msg.pk).exists()


@pytest.mark.xfail(reason="Arquivo não é removido ao deletar a mensagem")
def test_chat_message_file_handling(media_root, channel, admin_user):
    file = SimpleUploadedFile("file.txt", b"data")
    msg = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="file",
        arquivo=file,
    )
    assert msg.arquivo.name.startswith("chat/arquivos/")
    path = msg.arquivo.path
    assert os.path.exists(path)
    msg.delete()
    assert not os.path.exists(path)


def test_chat_notification_basic(channel, admin_user):
    msg = ChatMessage.objects.create(
        channel=channel,
        remetente=admin_user,
        tipo="text",
        conteudo="oi",
    )
    notif = ChatNotification.objects.create(usuario=admin_user, mensagem=msg)
    assert notif.lido is False
    notif.lido = True
    notif.save()
    notif.refresh_from_db()
    assert notif.lido is True


# Helpers
@pytest.fixture
def channel():
    return ChatChannel.objects.create(titulo="Conv", contexto_tipo="privado")
