import types

import pytest
from pywebpush import WebPushException

from notificacoes.models import PushSubscription
from notificacoes.push_sender import send

pytestmark = pytest.mark.django_db


def test_invalida_inscricao_quando_endpoint_invalido(admin_user, monkeypatch):
    sub = PushSubscription.objects.create(
        user=admin_user,
        device_id="d1",
        endpoint="https://example.com",
        p256dh="p",
        auth="a",
    )

    def fake_webpush(*args, **kwargs):
        response = types.SimpleNamespace(status_code=410)
        raise WebPushException("Gone", response=response)

    monkeypatch.setattr("notificacoes.push_sender.webpush", fake_webpush)

    send(admin_user, "payload")

    sub = PushSubscription.all_objects.get(id=sub.id)
    assert sub.deleted is True
