from unittest.mock import patch

import pytest

from chat.models import ChatChannel, ChatMessage, ChatNotification
from configuracoes.tasks import enviar_notificacoes_diarias, enviar_notificacoes_semanais

pytestmark = pytest.mark.django_db


def _criar_notificacao(user):
    channel = ChatChannel.objects.create(titulo="c", contexto_tipo="privado")
    msg = ChatMessage.objects.create(channel=channel, remetente=user, tipo="text", conteudo="oi")
    ChatNotification.objects.create(usuario=user, mensagem=msg)


@patch("configuracoes.tasks.enviar_para_usuario")
def test_tarefa_diaria_envia_resumo(mock_enviar, admin_user):
    config = admin_user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_enviar.assert_called_once()
    args = mock_enviar.call_args[0]
    assert args[0] == admin_user
    assert args[2]["chat"] == 1


@patch("configuracoes.tasks.enviar_para_usuario")
def test_tarefa_diaria_respeita_preferencia(mock_enviar, admin_user):
    config = admin_user.configuracao
    config.receber_notificacoes_email = False
    config.frequencia_notificacoes_email = "diaria"
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_enviar.assert_not_called()


@patch("configuracoes.tasks.enviar_notificacao_whatsapp")
def test_tarefa_semanal_whatsapp(mock_whatsapp, admin_user):
    config = admin_user.configuracao
    config.receber_notificacoes_whatsapp = True
    config.frequencia_notificacoes_whatsapp = "semanal"
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_semanais()
    mock_whatsapp.assert_called_once()
