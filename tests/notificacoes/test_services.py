import pytest

from accounts.factories import UserFactory
import pytest
from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationTemplate, UserNotificationPreference
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
    assert log.status == "pendente"
    assert log.destinatario.startswith(user.email[:2])


def test_enviar_sem_canais() -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    UserNotificationPreference.objects.filter(user=user).update(email=False)

    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "t", {})
    assert NotificationLog.objects.count() == 0


def test_template_inexistente() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "x", {})


def test_enviar_multiplos_canais(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="todos")
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.push = False
    prefs.whatsapp = True
    prefs.save()
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    assert called.get("count") == 2
    assert NotificationLog.objects.count() == 2
