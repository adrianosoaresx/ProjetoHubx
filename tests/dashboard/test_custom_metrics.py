import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from feed.factories import PostFactory
from feed.models import Post
from dashboard.models import DashboardCustomMetric
from dashboard.custom_metrics import DashboardCustomMetricService
from dashboard.services import DashboardMetricsService

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


def test_custom_metric_in_dashboard_metrics_service(admin_user, monkeypatch):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    metric = DashboardCustomMetric.objects.create(
        code="post_count",
        nome="Total Posts",
        descricao="",
        query_spec={
            "source": "posts",
            "aggregation": "count",
            "filters": {"organizacao_id": "$organizacao_id"},
            "icon": "fa-star",
        },
        escopo="organizacao",
    )
    from dashboard import views, constants

    monkeypatch.setattr(constants, "METRICAS_INFO", constants.METRICAS_INFO.copy())
    monkeypatch.setattr(views, "METRICAS_INFO", constants.METRICAS_INFO)
    metrics, metricas_info = DashboardMetricsService.get_metrics(
        admin_user, metricas=[metric.code], organizacao_id=admin_user.organizacao_id
    )
    assert metrics[metric.code]["total"] == 1
    assert metricas_info[metric.code]["label"] == "Total Posts"
    assert metricas_info[metric.code]["icon"] == "fa-star"
    assert metric.code not in views.METRICAS_INFO


def test_register_source_and_execute(admin_user, monkeypatch):
    monkeypatch.setattr(
        DashboardCustomMetricService,
        "SOURCES",
        DashboardCustomMetricService.SOURCES.copy(),
    )
    DashboardCustomMetricService.register_source("runtime_posts", Post, {"id"})
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    query = {
        "source": "runtime_posts",
        "aggregation": "count",
        "filters": {"organizacao_id": admin_user.organizacao_id},
    }
    assert (
        DashboardCustomMetricService.execute(query) == 1
    )


def test_register_source_invalid_field(monkeypatch):
    monkeypatch.setattr(
        DashboardCustomMetricService,
        "SOURCES",
        DashboardCustomMetricService.SOURCES.copy(),
    )
    with pytest.raises(ValueError):
        DashboardCustomMetricService.register_source("invalid", Post, {"foo"})

