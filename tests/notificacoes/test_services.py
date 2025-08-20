import pytest

from accounts.factories import UserFactory

from configuracoes.models import ConfiguracaoConta
from configuracoes.services import atualizar_preferencias_usuario
from notificacoes.models import (
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    UserNotificationPreference,
)

from notificacoes.services import notificacoes as svc
from notificacoes.services.whatsapp_client import send_whatsapp

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
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.email = False
    prefs.save(update_fields=["email"])

    svc.enviar_para_usuario(user, "t", {})
    log = NotificationLog.objects.get()
    assert log.status == NotificationStatus.FALHA
    assert log.erro == "Canais desabilitados pelo usuário"


def test_template_inexistente() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "x", {})


def test_enviar_multiplos_canais(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="todos")
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    assert called.get("count") == 3
    assert NotificationLog.objects.count() == 3


def test_enviar_para_usuario_respeita_push(monkeypatch) -> None:
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="p", assunto="Oi", corpo="C", canal="push")
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.push = False
    prefs.save(update_fields=["push"])
    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "p", {})
    assert called.get("count", 0) == 0
    log = NotificationLog.objects.get()
    assert log.status == NotificationStatus.FALHA


def test_send_whatsapp_requires_credentials(admin_user, settings):
    settings.TWILIO_SID = ""
    settings.TWILIO_TOKEN = ""
    settings.TWILIO_WHATSAPP_FROM = ""
    with pytest.raises(RuntimeError):
        send_whatsapp(admin_user, "oi")


def test_send_whatsapp_ok(admin_user, settings, monkeypatch):
    settings.TWILIO_SID = "sid"
    settings.TWILIO_TOKEN = "token"
    settings.TWILIO_WHATSAPP_FROM = "+123"

    called: dict[str, dict] = {}

    class DummyClient:
        def __init__(self, sid, token):  # pragma: no cover - simples
            self.messages = self

        def create(self, **kwargs):  # pragma: no cover - simples
            called["msg"] = kwargs

    monkeypatch.setattr(
        "notificacoes.services.whatsapp_client.TwilioClient", DummyClient
    )

    admin_user.whatsapp = "+551199999999"
    send_whatsapp(admin_user, "oi")
    assert called["msg"]["body"] == "oi"
