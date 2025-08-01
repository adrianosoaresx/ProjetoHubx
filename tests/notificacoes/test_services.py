import pytest

from accounts.factories import UserFactory
from notificacoes.models import (
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    UserNotificationPreference,
)
from notificacoes.services import notificacoes as svc

pytestmark = pytest.mark.django_db


def test_render_template() -> None:
    template = NotificationTemplate.objects.create(
        codigo="t", assunto="Oi {{ nome }}", corpo="C {{ valor }}", canal="email"
    )
    subject, body = svc.render_template(template, {"nome": "Ana", "valor": 10})
    assert subject == "Oi Ana"
    assert body == "C 10"


def test_enviar_para_usuario(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    log = NotificationLog.objects.get()
    assert called.get("count") == 1
    assert log.status == NotificationStatus.PENDENTE


def test_enviar_sem_canais(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    UserNotificationPreference.objects.filter(user=user).update(email=False)

    svc.enviar_para_usuario(user, "t", {})

    log = NotificationLog.objects.get()
    assert log.status == NotificationStatus.FALHA
    assert "desabilitados" in log.erro


def test_template_inexistente() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "x", {})
