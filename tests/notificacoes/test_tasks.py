import pytest
from celery.exceptions import Retry
from types import SimpleNamespace

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate
from notificacoes.tasks import enviar_notificacao_async
from notificacoes.services import metrics

pytestmark = pytest.mark.django_db


def test_enviar_notificacao_async_sucesso(settings, monkeypatch) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
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
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")

    def fake_send(*args, **kwargs):
        raise RuntimeError("erro")

    monkeypatch.setattr("notificacoes.tasks.send_email", fake_send)

    class DummyTask:
        def __init__(self) -> None:
            self.request = SimpleNamespace(retries=enviar_notificacao_async.max_retries)
            self.max_retries = enviar_notificacao_async.max_retries

        def retry(self, exc, countdown):  # pragma: no cover - not used here
            raise Retry()

    before_fail = metrics.notificacoes_falhadas_total.labels(canal="email")._value.get()
    with pytest.raises(RuntimeError):
        enviar_notificacao_async.run.__func__(DummyTask(), "Oi", "C", str(log.id))

    log.refresh_from_db()
    assert log.status == NotificationStatus.FALHA
    assert log.erro == "erro"
    assert metrics.notificacoes_falhadas_total.labels(canal="email")._value.get() == before_fail + 1


def test_enviar_notificacao_async_tenta_novamente(settings, monkeypatch) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email")
    chamadas = {"count": 0}

    def fake_send(*args, **kwargs):
        chamadas["count"] += 1
        if chamadas["count"] < 3:
            raise RuntimeError("temporario")

    monkeypatch.setattr("notificacoes.tasks.send_email", fake_send)

    class DummyTask:
        def __init__(self) -> None:
            self.request = SimpleNamespace(retries=0)
            self.max_retries = enviar_notificacao_async.max_retries

        def retry(self, exc, countdown):
            self.request.retries += 1
            raise Retry()

    task = DummyTask()
    before_success = metrics.notificacoes_enviadas_total.labels(canal="email")._value.get()
    before_fail = metrics.notificacoes_falhadas_total.labels(canal="email")._value.get()
    with pytest.raises(Retry):
        enviar_notificacao_async.run.__func__(task, "Oi", "C", str(log.id))
    log.refresh_from_db()
    assert log.status == NotificationStatus.PENDENTE

    with pytest.raises(Retry):
        enviar_notificacao_async.run.__func__(task, "Oi", "C", str(log.id))
    log.refresh_from_db()
    assert log.status == NotificationStatus.PENDENTE

    enviar_notificacao_async.run.__func__(task, "Oi", "C", str(log.id))
    log.refresh_from_db()
    assert log.status == NotificationStatus.ENVIADA
    assert chamadas["count"] == 3
    assert metrics.notificacoes_enviadas_total.labels(canal="email")._value.get() == before_success + 1
    assert metrics.notificacoes_falhadas_total.labels(canal="email")._value.get() == before_fail


def test_task_configuracao():
    assert enviar_notificacao_async.max_retries == 3
