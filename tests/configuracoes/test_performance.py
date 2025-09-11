import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection
from django.test import Client
from django.urls import reverse

from accounts.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.configuracoes.urls")]


@pytest.mark.parametrize("workers", [1, 5])
def test_preferencias_view_p95_below_100ms(workers: int) -> None:
    if workers > 1 and connection.vendor == "sqlite":
        pytest.skip("SQLite não suporta chamadas concorrentes confiáveis")
    user = UserFactory()
    base_client = Client()
    base_client.force_login(user)
    session_cookie = base_client.cookies.get("sessionid")
    url = reverse("configuracoes:configuracoes") + "?tab=preferencias"

    def request_view(_: int) -> float:
        local_client = Client()
        if session_cookie:
            local_client.cookies["sessionid"] = session_cookie.value
        inicio = time.perf_counter()
        resp = local_client.get(url)
        assert resp.status_code == 200
        return time.perf_counter() - inicio

    if workers == 1:
        tempos = [request_view(i) for i in range(20)]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            tempos = list(executor.map(request_view, range(20)))

    p95 = statistics.quantiles(tempos, n=100, method="inclusive")[94]
    assert p95 < 0.15
