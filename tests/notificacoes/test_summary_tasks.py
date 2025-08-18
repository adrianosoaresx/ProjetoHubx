import asyncio

import pytest
from channels.testing import WebsocketCommunicator
from django.utils import timezone
from freezegun import freeze_time

from accounts.factories import UserFactory
from Hubx.asgi import application
from notificacoes.models import (
    Canal,
    Frequencia,
    HistoricoNotificacao,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    PushSubscription,
)
from notificacoes.tasks import enviar_relatorios_diarios, enviar_relatorios_semanais

pytestmark = pytest.mark.django_db


def _criar_logs(user, canal, quantidade=2, offset_minutes=0):
    template, _ = NotificationTemplate.objects.get_or_create(
        codigo="t", defaults={"assunto": "a", "corpo": "msg", "canal": canal}
    )
    base_time = timezone.now() + timezone.timedelta(minutes=offset_minutes)
    for i in range(quantidade):
        NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            created_at=base_time + timezone.timedelta(seconds=i),
        )


@freeze_time("2024-01-01 08:00:00-03:00")
def test_relatorio_diario_cria_historico(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    config = user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_logs(user, Canal.EMAIL)

    enviar_relatorios_diarios()

    hist = HistoricoNotificacao.objects.get(user=user, canal=Canal.EMAIL, frequencia=Frequencia.DIARIA)
    assert len(hist.conteudo) == 2
    assert hist.data_referencia == timezone.localdate()
    assert all(log.status == NotificationStatus.ENVIADA for log in NotificationLog.objects.filter(user=user))


@freeze_time("2024-01-01 08:00:00-03:00")
def test_relatorio_diario_nao_duplicado(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    config = user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    _criar_logs(user, Canal.EMAIL)
    enviar_relatorios_diarios()
    _criar_logs(user, Canal.EMAIL, offset_minutes=1)
    enviar_relatorios_diarios()
    assert HistoricoNotificacao.objects.filter(user=user, canal=Canal.EMAIL, frequencia=Frequencia.DIARIA).count() == 1


@freeze_time("2024-01-01 08:00:00-03:00")
def test_relatorio_diario_respeita_horario(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    config = user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = (timezone.localtime() + timezone.timedelta(hours=1)).time()
    config.save()
    _criar_logs(user, Canal.EMAIL)

    enviar_relatorios_diarios()

    assert HistoricoNotificacao.objects.count() == 0


@freeze_time("2024-01-01 08:00:00-03:00")
def test_relatorio_diario_envia_push(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    user = UserFactory()
    config = user.configuracao
    config.frequencia_notificacoes_push = "diaria"
    config.hora_notificacao_diaria = timezone.localtime().time()
    config.save()
    PushSubscription.objects.create(
        user=user,
        device_id="d1",
        endpoint="https://example.com",
        p256dh="p",
        auth="a",
    )
    _criar_logs(user, Canal.PUSH)

    async def inner():
        communicator = WebsocketCommunicator(application, "/ws/notificacoes/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        await enviar_relatorios_diarios()
        resp = await communicator.receive_json_from()
        assert resp["canal"] == Canal.PUSH
        await communicator.disconnect()

    asyncio.run(inner())


@freeze_time("2024-01-01 08:00:00-03:00")
def test_relatorio_semanal_cria_historico(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    config = user.configuracao
    config.frequencia_notificacoes_email = "semanal"
    config.hora_notificacao_semanal = timezone.localtime().time()
    config.dia_semana_notificacao = timezone.localtime().weekday()
    config.save()
    _criar_logs(user, Canal.EMAIL)

    enviar_relatorios_semanais()

    hist = HistoricoNotificacao.objects.get(user=user, canal=Canal.EMAIL, frequencia=Frequencia.SEMANAL)
    assert len(hist.conteudo) == 2
    assert hist.data_referencia == timezone.localdate()
