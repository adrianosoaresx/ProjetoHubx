import pytest
from django.urls import reverse

from dashboard.services import DashboardMetricsService

pytest.importorskip("pytest_benchmark")
pytestmark = pytest.mark.django_db


def test_get_metrics_benchmark(benchmark, admin_user):
    benchmark(DashboardMetricsService.get_metrics, admin_user)


def test_dashboard_view_benchmark(benchmark, client, admin_user):
    client.force_login(admin_user)
    benchmark(lambda: client.get(reverse("dashboard:admin")))


def test_dashboard_view_p95(client, admin_user):
    client.force_login(admin_user)
    import time

    times = []
    for _ in range(20):
        start = time.perf_counter()
        resp = client.get(reverse("dashboard:admin"))
        assert resp.status_code == 200
        times.append(time.perf_counter() - start)
    times.sort()
    p95 = times[int(len(times) * 0.95) - 1]
    assert p95 < 0.25
