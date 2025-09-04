import pytest

from accounts.factories import UserFactory
from notificacoes.models import (
    Canal,
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
    UserNotificationPreference,
    PushSubscription,
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
    assert log.erro == "Canal email desabilitado pelo usuário"
    assert log.destinatario.startswith(user.email[:2])


def test_template_inexistente() -> None:
    user = UserFactory()
    with pytest.raises(ValueError):
        svc.enviar_para_usuario(user, "x", {})


def test_enviar_multiplos_canais(monkeypatch, settings) -> None:
    settings.ONESIGNAL_ENABLED = True
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


def test_enviar_todos_sem_canais(settings) -> None:
    settings.ONESIGNAL_ENABLED = True
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="todos")
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.email = False
    prefs.push = False
    prefs.whatsapp = False
    prefs.save(update_fields=["email", "push", "whatsapp"])

    user.whatsapp = "+551199999999"
    user.save(update_fields=["whatsapp"])
    PushSubscription.objects.create(
        user=user,
        device_id="dev1",
        endpoint="e",
        p256dh="p",
        auth="a",
    )

    svc.enviar_para_usuario(user, "t", {})

    logs = NotificationLog.objects.all()
    assert logs.count() == 3
    assert {log.canal for log in logs} == {Canal.EMAIL, Canal.PUSH, Canal.WHATSAPP}
    for log in logs:
        assert log.status == NotificationStatus.FALHA
    erro_por_canal = {log.canal: log.erro for log in logs}
    dest_por_canal = {log.canal: log.destinatario for log in logs}
    assert erro_por_canal[Canal.EMAIL] == "Canal email desabilitado pelo usuário"
    assert erro_por_canal[Canal.PUSH] == "Canal push desabilitado pelo usuário"
    assert erro_por_canal[Canal.WHATSAPP] == "Canal whatsapp desabilitado pelo usuário"
    assert dest_por_canal[Canal.EMAIL].startswith(user.email[:2])
    assert dest_por_canal[Canal.WHATSAPP] == user.whatsapp
    assert dest_por_canal[Canal.PUSH] == "dev1"


def test_enviar_todos_com_canais_desativados(monkeypatch, settings) -> None:
    settings.ONESIGNAL_ENABLED = True
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="todos")
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.push = False
    prefs.save(update_fields=["push"])

    user.whatsapp = "+551199999999"
    user.save(update_fields=["whatsapp"])
    PushSubscription.objects.create(
        user=user,
        device_id="dev1",
        endpoint="e",
        p256dh="p",
        auth="a",
    )

    called = {}

    def fake_delay(*args, **kwargs):
        called["count"] = called.get("count", 0) + 1

    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay",
        fake_delay,
    )

    svc.enviar_para_usuario(user, "t", {})

    assert called.get("count") == 2

    logs = NotificationLog.objects.all()
    assert logs.count() == 3
    status_por_canal = {log.canal: log.status for log in logs}
    assert status_por_canal[Canal.PUSH] == NotificationStatus.FALHA
    assert status_por_canal[Canal.EMAIL] == NotificationStatus.PENDENTE
    assert status_por_canal[Canal.WHATSAPP] == NotificationStatus.PENDENTE
    push_log = next(log for log in logs if log.canal == Canal.PUSH)
    assert push_log.erro == "Canal push desabilitado pelo usuário"
    assert push_log.destinatario == "dev1"
    email_log = next(log for log in logs if log.canal == Canal.EMAIL)
    assert email_log.destinatario.startswith(user.email[:2])
    whatsapp_log = next(log for log in logs if log.canal == Canal.WHATSAPP)
    assert whatsapp_log.destinatario == user.whatsapp


def test_enviar_para_usuario_respeita_push(monkeypatch, settings) -> None:
    settings.ONESIGNAL_ENABLED = True
    user = UserFactory()
    NotificationTemplate.objects.create(codigo="p", assunto="Oi", corpo="C", canal="push")
    prefs = UserNotificationPreference.objects.get(user=user)
    prefs.push = False
    prefs.save(update_fields=["push"])
    PushSubscription.objects.create(
        user=user,
        device_id="dev1",
        endpoint="e",
        p256dh="p",
        auth="a",
    )
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
    assert log.erro == "Canal push desabilitado pelo usuário"
    assert log.destinatario == "dev1"


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

    monkeypatch.setattr("notificacoes.services.whatsapp_client.TwilioClient", DummyClient)

    admin_user.whatsapp = "+551199999999"
    send_whatsapp(admin_user, "oi")
    assert called["msg"]["body"] == "oi"
