import pytest
from django.urls import reverse

from core.metrics import ENDPOINT_LATENCY


@pytest.mark.django_db
def test_endpoint_latency_records_metric(client):
    ENDPOINT_LATENCY.clear()
    client.get(reverse("core:home"))
    metric = ENDPOINT_LATENCY.labels("GET", "core:home")
    assert metric._sum.get() > 0
