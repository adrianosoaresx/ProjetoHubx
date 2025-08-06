import pytest
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationTemplate

pytestmark = pytest.mark.django_db


def test_enviar_api(monkeypatch) -> None:
    admin_user = UserFactory(is_staff=True)
    NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    called: dict[str, int] = {"count": 0}

    def fake_delay(*args, **kwargs):
        called["count"] += 1

    monkeypatch.setattr("notificacoes.services.notificacoes.enviar_notificacao_async.delay", fake_delay)

    client = APIClient()
    client.force_authenticate(user=admin_user)
    resp = client.post(
        "/api/notificacoes/enviar/",
        {"template_codigo": "t", "user_id": admin_user.id, "context": {}},
        format="json",
    )
    assert resp.status_code == 204
    assert called["count"] == 1


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
