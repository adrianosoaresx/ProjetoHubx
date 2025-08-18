from unittest.mock import patch

import pytest
from django.utils import timezone
from freezegun import freeze_time

from chat.models import ChatChannel, ChatMessage, ChatNotification
from configuracoes.tasks import (
    enviar_notificacao_whatsapp,
    enviar_notificacoes_diarias,
    enviar_notificacoes_semanais,
)

pytestmark = pytest.mark.django_db


def _criar_notificacao(user):
    channel = ChatChannel.objects.create(titulo="c", contexto_tipo="privado")
    msg = ChatMessage.objects.create(channel=channel, remetente=user, tipo="text", conteudo="oi")
    ChatNotification.objects.create(usuario=user, mensagem=msg)


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.enviar_para_usuario")
def test_tarefa_diaria_envia_resumo(mock_enviar, admin_user):
    config = admin_user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_enviar.assert_called_once()
    args = mock_enviar.call_args[0]
    assert args[0] == admin_user
    assert args[2]["chat"] == 1


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.enviar_para_usuario")
def test_tarefa_diaria_respeita_preferencia(mock_enviar, admin_user):
    config = admin_user.configuracao
    config.receber_notificacoes_email = False
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_enviar.assert_not_called()


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.enviar_para_usuario")
def test_tarefa_diaria_envia_resumo_push(mock_enviar, admin_user):
    config = admin_user.configuracao
    config.frequencia_notificacoes_push = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_enviar.assert_called_once()


@patch("configuracoes.tasks.Client")
def test_enviar_notificacao_whatsapp(mock_client, admin_user):
    instance = mock_client.return_value
    enviar_notificacao_whatsapp(admin_user, {"chat": 1, "feed": 0, "eventos": 0})
    instance.messages.create.assert_called_once()


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.enviar_notificacao_whatsapp")
def test_tarefa_semanal_whatsapp(mock_whatsapp, admin_user):
    config = admin_user.configuracao
    config.receber_notificacoes_whatsapp = True
    config.frequencia_notificacoes_whatsapp = "semanal"
    config.hora_notificacao_semanal = timezone.localtime().time()
    config.dia_semana_notificacao = timezone.localtime().weekday()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_semanais()
    mock_whatsapp.assert_called_once()


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.Evento")
@patch("configuracoes.tasks.send_push")
def test_tarefa_diaria_envia_push(mock_push, mock_evento, admin_user):
    mock_evento.objects.filter.return_value.exclude.return_value.count.return_value = 0
    config = admin_user.configuracao
    config.receber_notificacoes_push = True
    config.frequencia_notificacoes_push = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_push.assert_called_once()


@freeze_time("2024-01-01 08:00:00-03:00")
@patch("configuracoes.tasks.Evento")
@patch("configuracoes.tasks.send_push")
def test_tarefa_diaria_push_respeita_preferencia(mock_push, mock_evento, admin_user):
    mock_evento.objects.filter.return_value.exclude.return_value.count.return_value = 0
    config = admin_user.configuracao
    config.receber_notificacoes_push = False
    config.frequencia_notificacoes_push = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_notificacao(admin_user)
    enviar_notificacoes_diarias()
    mock_push.assert_not_called()
