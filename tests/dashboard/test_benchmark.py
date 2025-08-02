import pytest
from django.urls import reverse

from dashboard.services import DashboardMetricsService

pytest.importorskip("pytest_benchmark")
pytestmark = pytest.mark.django_db


def test_get_metrics_benchmark(benchmark, admin_user):
    benchmark(DashboardMetricsService.get_metrics, admin_user)


def test_dashboard_view_benchmark(benchmark, client, admin_user):
    client.force_login(admin_user)
    benchmark(lambda: client.get(reverse('dashboard:admin')))
