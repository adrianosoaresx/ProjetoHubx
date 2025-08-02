import pytest
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationTemplate

pytestmark = pytest.mark.django_db


def test_enviar_api(monkeypatch) -> None:
    admin_user = UserFactory(is_staff=True)
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    called = {}

    def fake_send(user, codigo, ctx):
        called["user"] = user

    monkeypatch.setattr("notificacoes.services.notificacoes.enviar_para_usuario", fake_send)
    monkeypatch.setattr(
        "notificacoes.services.notificacoes.enviar_notificacao_async.delay", lambda *a, **k: None
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post(
        "/api/notificacoes/enviar/",
        {"template_codigo": "t", "user_id": admin_user.id, "context": {}},
        format="json",
    )
    assert resp.status_code == 204
    assert called["user"] == admin_user


def test_logs_filtrados_por_usuario(client) -> None:
    admin_user = UserFactory(is_staff=True)
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    NotificationLog.objects.create(user=admin_user, template=template, canal="email")
    user2 = UserFactory()
    NotificationLog.objects.create(user=user2, template=template, canal="email")

    client.force_login(user2)
    resp = client.get("/api/notificacoes/logs/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
