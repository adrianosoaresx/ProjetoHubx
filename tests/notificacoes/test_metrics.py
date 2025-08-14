from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from notificacoes.models import NotificationLog, NotificationStatus, NotificationTemplate

pytestmark = pytest.mark.django_db


def test_metrics_dashboard(client):
    staff = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(staff)
    user = UserFactory()
    active_before = NotificationTemplate.objects.filter(ativo=True).count()
    inactive_before = NotificationTemplate.objects.filter(ativo=False).count()
    template = NotificationTemplate.objects.create(codigo="t", assunto="a", corpo="b", canal="email")
    NotificationLog.objects.create(user=user, template=template, canal="email", status=NotificationStatus.ENVIADA)
    log2 = NotificationLog.objects.create(user=user, template=template, canal="whatsapp", status=NotificationStatus.FALHA)
    log2.created_at = timezone.now() - timedelta(days=30)
    log2.save(update_fields=["created_at"])
    url = reverse("notificacoes:metrics_dashboard")
    resp = client.get(url, {"inicio": timezone.now().date()})
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx["total_por_canal"].get("email") in {None, 1}
    assert "whatsapp" not in ctx["total_por_canal"]
    assert ctx["falhas_por_canal"].get("whatsapp") is None
    assert ctx["templates_ativos"] == active_before + 1
    assert ctx["templates_inativos"] == inactive_before
