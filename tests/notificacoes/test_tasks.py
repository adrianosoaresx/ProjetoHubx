import pytest
from celery.exceptions import Retry

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate
from notificacoes.tasks import enviar_notificacao_async
from notificacoes.services import metrics

pytestmark = pytest.mark.django_db


def test_enviar_notificacao_async_sucesso(settings, monkeypatch) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    called = {}

    def fake_send(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr("notificacoes.tasks.send_email", fake_send)

    before = metrics.notificacoes_enviadas_total.labels(canal="email")._value.get()
    enviar_notificacao_async("Oi", "C", str(log.id))

    assert called.get("count") == 1
    log.refresh_from_db()
    assert log.status == NotificationStatus.ENVIADA
    assert log.data_envio is not None
    assert metrics.notificacoes_enviadas_total.labels(canal="email")._value.get() == before + 1


def test_enviar_notificacao_async_falha(settings, monkeypatch) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")

    def fake_send(*args, **kwargs):
        raise RuntimeError("erro")

    monkeypatch.setattr("notificacoes.tasks.send_email", fake_send)

    before_fail = metrics.notificacoes_falhas_total.labels(canal="email")._value.get()
    with pytest.raises(RuntimeError):
        enviar_notificacao_async("Oi", "C", str(log.id))

    log.refresh_from_db()
    assert log.status == NotificationStatus.FALHA
    assert log.erro == "erro"
    assert (
        metrics.notificacoes_falhas_total.labels(canal="email")._value.get()
        == before_fail + 1
    )


def test_task_configuracao():
    assert enviar_notificacao_async.max_retries == 3
