from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate

pytestmark = pytest.mark.django_db


def _create_logs(user):
    template = NotificationTemplate.objects.create(codigo="t", assunto="a", corpo="b", canal="email")
    NotificationLog.objects.create(
        user=user,
        template=template,
        canal="email",
        status=NotificationStatus.ENVIADA,
        data_envio=timezone.now(),
    )
    NotificationLog.objects.create(
        user=user,
        template=template,
        canal="whatsapp",
        status=NotificationStatus.FALHA,
        data_envio=timezone.now() - timedelta(days=30),
    )
    return template


def test_metrics_dashboard_without_filters(client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    user = UserFactory()

    active_before = NotificationTemplate.objects.filter(ativo=True).count()

    _create_logs(user)
    url = reverse("notificacoes:metrics_dashboard")
    resp = client.get(url)
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["form"].is_bound is False
    assert ctx["total_por_canal"].get("email") == 1
    assert ctx["falhas_por_canal"].get("whatsapp") == 1
    assert ctx["templates_total"] == active_before + 1


def test_metrics_dashboard_with_filters(client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    user = UserFactory()

    active_before = NotificationTemplate.objects.filter(ativo=True).count()

    _create_logs(user)
    url = reverse("notificacoes:metrics_dashboard")
    resp = client.get(url, {"inicio": timezone.now().date()})
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["form"].is_bound is True
    assert ctx["form"].is_valid()
    assert ctx["total_por_canal"].get("email") == 1
    assert ctx["total_por_canal"].get("whatsapp") is None
    assert ctx["falhas_por_canal"].get("whatsapp") is None
    assert ctx["templates_total"] == active_before + 1
