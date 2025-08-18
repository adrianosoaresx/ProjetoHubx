import pytest
from django.test.utils import override_settings

from dashboard.services import DashboardMetricsService

pytestmark = pytest.mark.django_db


def test_cache_fallback_without_redis(admin_user):
    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        }
    ):
        metrics1 = DashboardMetricsService.get_metrics(admin_user)
        metrics2 = DashboardMetricsService.get_metrics(admin_user)
        assert metrics1 == metrics2
