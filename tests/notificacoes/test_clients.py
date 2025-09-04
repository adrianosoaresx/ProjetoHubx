import logging
import sys
import types

import httpx
import pytest
from onesignal_sdk.error import OneSignalHTTPError

from accounts.factories import UserFactory
from notificacoes.models import PushSubscription
from notificacoes.services.email_client import send_email
from notificacoes.services.push_client import send_push
from notificacoes.services.whatsapp_client import send_whatsapp

pytestmark = pytest.mark.django_db


def test_send_email_success(monkeypatch, settings, caplog):
    user = UserFactory(email="test@example.com")
    settings.DEFAULT_FROM_EMAIL = "from@example.com"
    called = {}

    def fake_send_mail(subject, body, from_email, recipient_list):
        called["args"] = (subject, body, from_email, recipient_list)

    monkeypatch.setattr("notificacoes.services.email_client.send_mail", fake_send_mail)
    with caplog.at_level(logging.INFO):
        send_email(user, "sub", "body")
    assert called["args"][0] == "sub"
    assert "email_enviado" in caplog.text


def test_send_email_failure(monkeypatch, settings):
    user = UserFactory(email="test@example.com")
    settings.DEFAULT_FROM_EMAIL = "from@example.com"

    def fake_send_mail(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr("notificacoes.services.email_client.send_mail", fake_send_mail)
    with pytest.raises(RuntimeError):
        send_email(user, "s", "b")


def test_send_whatsapp_success(monkeypatch, settings, caplog):
    user = UserFactory(whatsapp="+551199999999")
    settings.TWILIO_SID = "sid"
    settings.TWILIO_TOKEN = "token"
    settings.TWILIO_WHATSAPP_FROM = "whatsapp:+11111111111"

    class FakeMessages:
        def create(self, **kwargs):
            return None

    class FakeClient:
        def __init__(self, sid, token):
            self.messages = FakeMessages()

    module = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "twilio.rest", module)
    with caplog.at_level(logging.INFO):
        send_whatsapp(user, "ola")
    assert "whatsapp_enviado" in caplog.text


def test_send_push_success(monkeypatch, settings, caplog):
    user = UserFactory()
    settings.ONESIGNAL_APP_ID = "app"
    settings.ONESIGNAL_API_KEY = "key"
    settings.ONESIGNAL_ENABLED = True

    class FakeClient:
        def __init__(self, app_id, rest_api_key):
            self.sent = False

        def send_notification(self, data):
            self.sent = True

    module = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "onesignal_sdk.client", module)
    with caplog.at_level(logging.INFO):
        send_push(user, "msg")
    assert "push_enviado" in caplog.text


def test_send_push_invalida_inscricao(monkeypatch, settings, caplog):
    user = UserFactory()
    settings.ONESIGNAL_APP_ID = "app"
    settings.ONESIGNAL_API_KEY = "key"
    settings.ONESIGNAL_ENABLED = True
    sub = PushSubscription.objects.create(
        user=user,
        device_id="d1",
        endpoint="https://example.com",
        p256dh="p",
        auth="a",
    )

    class FakeClient:
        def __init__(self, app_id, rest_api_key):
            pass

        def send_notification(self, data):
            response = httpx.Response(410, json={"errors": ["d1"]})
            raise OneSignalHTTPError(response)

    module = types.SimpleNamespace(Client=FakeClient)
    monkeypatch.setitem(sys.modules, "onesignal_sdk.client", module)
    with caplog.at_level(logging.INFO):
        send_push(user, "msg")
    sub.refresh_from_db()
    assert sub.ativo is False
    assert "push_inscricao_inativa" in caplog.text
