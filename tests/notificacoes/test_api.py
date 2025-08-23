import pytest
from django.test.utils import override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from notificacoes.models import (
    NotificationLog,
    NotificationStatus,
    NotificationTemplate,
)

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


def test_logs_incluem_campo_created_at(client) -> None:
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t3", assunto="Oi", corpo="C", canal="email")
    NotificationLog.objects.create(user=user, template=template, canal="email")

    client.force_login(user)
    resp = client.get("/api/notificacoes/logs/")
    assert resp.status_code == 200
    primeiro = resp.json()[0]
    assert "created_at" in primeiro


def test_usuario_pode_marcar_notificacao_como_lida(client) -> None:
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email", status=NotificationStatus.ENVIADA)
    client.force_login(user)
    resp = client.patch(
        f"/api/notificacoes/logs/{log.id}/",
        {"status": NotificationStatus.LIDA},
        content_type="application/json",
    )
    assert resp.status_code == 204
    log.refresh_from_db()
    assert log.status == NotificationStatus.LIDA
    assert log.data_leitura is not None


def test_usuario_nao_pode_usar_status_invalido(client) -> None:
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t9", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(user=user, template=template, canal="email", status=NotificationStatus.ENVIADA)
    client.force_login(user)
    resp = client.patch(
        f"/api/notificacoes/logs/{log.id}/",
        {"status": NotificationStatus.FALHA},
        content_type="application/json",
    )
    assert resp.status_code == 400
    log.refresh_from_db()
    assert log.status == NotificationStatus.ENVIADA


def test_usuario_nao_pode_marcar_log_nao_enviado(client) -> None:
    user = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t10", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(
        user=user, template=template, canal="email", status=NotificationStatus.PENDENTE
    )
    client.force_login(user)
    resp = client.patch(
        f"/api/notificacoes/logs/{log.id}/",
        {"status": NotificationStatus.LIDA},
        content_type="application/json",
    )
    assert resp.status_code == 400
    log.refresh_from_db()
    assert log.status == NotificationStatus.PENDENTE


def test_usuario_nao_marca_notificacao_de_outro(client) -> None:
    user1 = UserFactory()
    user2 = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t2", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(
        user=user1, template=template, canal="email", status=NotificationStatus.ENVIADA
    )
    client.force_login(user2)
    resp = client.patch(
        f"/api/notificacoes/logs/{log.id}/",
        {"status": NotificationStatus.LIDA},
        content_type="application/json",
    )
    assert resp.status_code == 404


@override_settings(ROOT_URLCONF="notificacoes.api_urls")
def test_usuario_staff_nao_marca_notificacao_de_outro(client) -> None:
    staff = UserFactory(is_staff=True)
    other = UserFactory()
    template = NotificationTemplate.objects.create(codigo="t8", assunto="Oi", corpo="C", canal="email")
    log = NotificationLog.objects.create(
        user=other, template=template, canal="email", status=NotificationStatus.ENVIADA
    )
    client.force_login(staff)
    resp = client.patch(
        f"/logs/{log.id}/",
        {"status": NotificationStatus.LIDA},
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_nao_exclui_template_com_logs(client) -> None:
    admin_user = UserFactory(is_staff=True)
    template = NotificationTemplate.objects.create(codigo="t4", assunto="Oi", corpo="C", canal="email")
    NotificationLog.objects.create(user=admin_user, template=template, canal="email")
    client.force_login(admin_user)
    resp = client.delete(f"/api/notificacoes/templates/{template.id}/")
    assert resp.status_code == 400
    assert NotificationTemplate.objects.filter(id=template.id).exists()


def test_exclui_template_sem_logs(client) -> None:
    admin_user = UserFactory(is_staff=True)
    template = NotificationTemplate.objects.create(codigo="t5", assunto="Oi", corpo="C", canal="email")
    client.force_login(admin_user)
    resp = client.delete(f"/api/notificacoes/templates/{template.id}/")
    assert resp.status_code == 204
    assert not NotificationTemplate.objects.filter(id=template.id).exists()
