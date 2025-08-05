import pytest
from django.contrib.auth import get_user_model

from chat.models import ChatParticipant
from chat.services import adicionar_reacao, criar_canal, enviar_mensagem
from nucleos.models import ParticipacaoNucleo

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_criar_canal_adiciona_participantes(admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    participantes = ChatParticipant.objects.filter(channel=canal)
    assert participantes.count() == 2
    owner = participantes.get(user=admin_user)
    assert owner.is_owner and owner.is_admin


def test_criar_canal_valida_contexto_nucleo(
    coordenador_user, admin_user, associado_user, nucleo
):
    """Garante que apenas usuários do núcleo informado participem."""
    ParticipacaoNucleo.objects.create(
        user=coordenador_user, nucleo=nucleo, status="aprovado"
    )
    ParticipacaoNucleo.objects.create(
        user=admin_user, nucleo=nucleo, status="aprovado"
    )
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


def test_enviar_mensagem_valida_participacao(admin_user, coordenador_user, associado_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    msg = enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    assert msg.conteudo == "oi"
    with pytest.raises(PermissionError):
        enviar_mensagem(canal, associado_user, "text", conteudo="ola")


def test_adicionar_reacao_incrementa(admin_user, coordenador_user):
    canal = criar_canal(
        criador=admin_user,
        contexto_tipo="privado",
        contexto_id=None,
        titulo="Privado",
        descricao="",
        participantes=[coordenador_user],
    )
    msg = enviar_mensagem(canal, admin_user, "text", conteudo="oi")
    adicionar_reacao(msg, "👍")
    msg.refresh_from_db()
    assert msg.reactions["👍"] == 1
