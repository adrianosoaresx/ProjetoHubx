import pytest
from django.urls import reverse

from dashboard.views import METRICAS_INFO
from dashboard.services import DashboardMetricsService

pytestmark = pytest.mark.django_db


def test_metricas_info_used_in_context(client, admin_user):
    client.force_login(admin_user)
    resp = client.get(reverse("dashboard:admin"))
    expected = [{"key": k, "label": v["label"]} for k, v in METRICAS_INFO.items()]
    assert resp.context["metricas_disponiveis"] == expected


def test_error_message_rendered(client, admin_user, monkeypatch):
    client.force_login(admin_user)

    def boom(user, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(DashboardMetricsService, "get_metrics", boom)
    resp = client.get(reverse("dashboard:metrics-partial"), HTTP_HX_REQUEST="true")
    assert resp.status_code == 400
    assert "boom" in resp.content.decode()
