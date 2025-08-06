import pytest
from django.utils import timezone
from freezegun import freeze_time

from accounts.factories import UserFactory
from notificacoes.models import (
    Canal,
    HistoricoNotificacao,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
)
from notificacoes.tasks import enviar_relatorios_diarios, enviar_relatorios_semanais

pytestmark = pytest.mark.django_db


def _criar_logs(user, canal, quantidade=2):
    template = NotificationTemplate.objects.create(
        codigo="t", assunto="a", corpo="msg", canal=canal
    )
    for i in range(quantidade):
        NotificationLog.objects.create(
            user=user,
            template=template,
            canal=canal,
            created=timezone.now() + timezone.timedelta(seconds=i),
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

    hist = HistoricoNotificacao.objects.get(user=user, canal=Canal.EMAIL)
    assert len(hist.conteudo) == 2
    assert all(
        log.status == NotificationStatus.ENVIADA
        for log in NotificationLog.objects.filter(user=user)
    )


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

    hist = HistoricoNotificacao.objects.get(user=user, canal=Canal.EMAIL)
    assert len(hist.conteudo) == 2
