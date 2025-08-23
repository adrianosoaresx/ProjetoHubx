import pytest
from django.contrib.auth import get_user_model

from django.core.files.uploadedfile import SimpleUploadedFile

from chat.models import ChatAttachment, ChatParticipant
from chat.services import adicionar_reacao, remover_reacao, criar_canal, enviar_mensagem
from nucleos.models import ParticipacaoNucleo

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_criar_canal_adiciona_participantes(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    participantes = ChatParticipant.objects.filter(channel=canal)
    assert participantes.count() == 2
    owner = participantes.get(user=admin_user)
    assert owner.is_owner and owner.is_admin


def test_criar_canal_privado_sem_nucleo(admin_user):
    with pytest.raises(PermissionError):
        criar_canal(
            criador=admin_user,
            contexto_tipo="privado",
            contexto_id=None,
            titulo="Privado",
            descricao="",
            participantes=[],
        )


def test_criar_canal_valida_contexto_nucleo(
    coordenador_user, admin_user, associado_user, nucleo
):
    """Garante que apenas usuários do núcleo informado participem."""
    criar_canal(
        criador=coordenador_user,
        contexto_tipo="nucleo",
        contexto_id=nucleo.id,
        titulo="",
        descricao="",
        participantes=[admin_user],
    )
    with pytest.raises(PermissionError):
        criar_canal(
            criador=coordenador_user,
            contexto_tipo="nucleo",
            contexto_id=nucleo.id,
            titulo="",
            descricao="",
            participantes=[associado_user],
        )
    with pytest.raises(PermissionError):
        criar_canal(
            criador=associado_user,
            contexto_tipo="nucleo",
            contexto_id=nucleo.id,
            titulo="",
            descricao="",
            participantes=[],
        )


def test_criar_canal_privado_valida_nucleo(
    admin_user, coordenador_user, associado_user, nucleo
):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="",
        descricao="",
        participantes=[coordenador_user],
    )
    assert canal.contexto_id == nucleo.id
    with pytest.raises(PermissionError):
        criar_canal(
            criador=admin_user,
            contexto_tipo="privado",
            contexto_id=nucleo.id,
            titulo="",
            descricao="",
            participantes=[associado_user],
        )
    with pytest.raises(PermissionError):
        criar_canal(
            criador=associado_user,
            contexto_tipo="privado",
            contexto_id=nucleo.id,
            titulo="",
            descricao="",
            participantes=[coordenador_user],
        )


def test_enviar_mensagem_valida_participacao(admin_user, coordenador_user, associado_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    msg = enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    assert msg.conteudo == "oi"
    with pytest.raises(PermissionError):
        enviar_mensagem(canal, associado_user, "text", conteudo="ola")


def test_enviar_mensagem_url_sem_arquivo(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    url = "https://example.com/img.png"
    msg = enviar_mensagem(canal, admin_user, "image", conteudo=url)
    assert msg.conteudo == url and not msg.arquivo
    with pytest.raises(ValueError):
        enviar_mensagem(canal, admin_user, "image", conteudo="not-url")


def test_enviar_mensagem_reply_to(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    msg1 = enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    msg2 = enviar_mensagem(canal, admin_user, "text", conteudo="ola", reply_to=msg1)
    assert msg2.reply_to == msg1


def test_enviar_mensagem_reply_to_invalid_channel(admin_user, coordenador_user, nucleo):
    canal1 = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    canal2 = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado2",
        descricao="",
        participantes=[coordenador_user],
    )
    msg1 = enviar_mensagem(canal1, admin_user, "text", conteudo="oi")
    with pytest.raises(ValueError):
        enviar_mensagem(canal2, admin_user, "text", conteudo="ola", reply_to=msg1)


def test_adicionar_reacao_incrementa_e_limita(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    msg = enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    adicionar_reacao(msg, admin_user, "👍")
    adicionar_reacao(msg, admin_user, "👍")  # segunda reação não duplica
    adicionar_reacao(msg, coordenador_user, "👍")
    assert msg.reaction_counts()["👍"] == 2
    remover_reacao(msg, admin_user, "👍")
    assert msg.reaction_counts()["👍"] == 1


def test_enviar_mensagem_com_attachment_id(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    att = ChatAttachment.objects.create(
        arquivo=SimpleUploadedFile("a.txt", b"a"),
        tamanho=1,
        usuario=admin_user,
    )
    msg = enviar_mensagem(canal, admin_user, "file", attachment_id=str(att.id))
    att.refresh_from_db()
    assert att.mensagem_id == msg.id
    assert msg.arquivo.name == att.arquivo.name


def test_enviar_mensagem_recusa_attachment_infectado(admin_user, coordenador_user, nucleo):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=nucleo.id,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    att = ChatAttachment.objects.create(
        arquivo=SimpleUploadedFile("a.txt", b"a"),
        tamanho=1,
        usuario=admin_user,
        infected=True,
    )
    with pytest.raises(ValueError):
        enviar_mensagem(canal, admin_user, "file", attachment_id=str(att.id))
