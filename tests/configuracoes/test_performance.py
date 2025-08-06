import statistics
import time

import pytest
from django.urls import reverse

from accounts.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.configuracoes.urls")]


def test_preferencias_view_p95_below_100ms(client):
    user = UserFactory()
    client.force_login(user)
    url = reverse("configuracoes") + "?tab=preferencias"
    tempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        resp = client.get(url)
        assert resp.status_code == 200
        tempos.append(time.perf_counter() - inicio)
    p95 = statistics.quantiles(tempos, n=100, method="inclusive")[94]
    assert p95 < 0.1
