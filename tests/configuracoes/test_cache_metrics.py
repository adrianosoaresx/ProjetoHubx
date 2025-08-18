import pytest

from configuracoes import metrics
from configuracoes.services import get_user_preferences

pytestmark = pytest.mark.django_db


def test_metrics_counters_increment(admin_user):
    metrics.config_cache_hits_total._value.set(0)
    metrics.config_cache_misses_total._value.set(0)
    get_user_preferences(admin_user)
    get_user_preferences(admin_user)
    assert metrics.config_cache_misses_total._value.get() == 1
    assert metrics.config_cache_hits_total._value.get() == 1


def test_latency_histogram(admin_user):
    metrics.config_get_latency_seconds.clear()
    get_user_preferences(admin_user)
    sample = metrics.config_get_latency_seconds.collect()[0]
    assert sample.samples
