import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate
from notificacoes.tasks import enviar_notificacao_async

pytestmark = pytest.mark.django_db


def test_enviar_notificacao_async(settings, monkeypatch) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(
        user=user, template=template, canal="email", status=NotificationStatus.ENVIADA, data_envio=timezone.now()
    )
    called = {}

    def fake_send(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr("notificacoes.tasks.send_email", fake_send)

    enviar_notificacao_async(user.id, template.id, "email", "Oi", "C", log.id)

    assert called.get("count") == 1
    log.refresh_from_db()
    assert log.status == NotificationStatus.ENVIADA
