import time

import pytest
from django.test import override_settings
from django.urls import reverse

pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF="tests.configuracoes.urls")
def test_configuracoes_view_p95_below_threshold(admin_client):
    url = reverse("configuracoes")
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        resp = admin_client.get(url)
        assert resp.status_code == 200
        samples.append(time.perf_counter() - start)
    samples.sort()
    p95 = samples[int(len(samples) * 95 / 100) - 1]
    assert p95 < 0.1
