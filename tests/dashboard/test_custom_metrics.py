import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from feed.factories import PostFactory
from dashboard.models import DashboardCustomMetric
from dashboard.custom_metrics import DashboardCustomMetricService

pytestmark = pytest.mark.django_db


def test_custom_metric_service(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    metric = DashboardCustomMetric.objects.create(
        code="post_count",
        nome="Total Posts",
        descricao="",
        query_spec={
            "source": "posts",
            "aggregation": "count",
            "filters": {"organizacao_id": "$organizacao_id"},
        },
        escopo="organizacao",
    )
    total = DashboardCustomMetricService.execute(
        metric.query_spec, organizacao_id=admin_user.organizacao_id
    )
    assert total == 1


def test_custom_metric_api(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    metric = DashboardCustomMetric.objects.create(
        code="post_count",
        nome="Total Posts",
        descricao="",
        query_spec={
            "source": "posts",
            "aggregation": "count",
            "filters": {"organizacao_id": "$organizacao_id"},
        },
        escopo="organizacao",
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = (
        reverse("dashboard_api:dashboard-custom-metric-execute", args=[metric.id])
        + f"?organizacao_id={admin_user.organizacao_id}"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

