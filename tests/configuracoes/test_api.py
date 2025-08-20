from __future__ import annotations

import pytest
import time
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.configuracoes.urls")]


@pytest.fixture
def api_client():
    return APIClient()


def test_update_preferences(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("configuracoes_api:configuracoes-conta")
    data = {
        "receber_notificacoes_email": False,
        "frequencia_notificacoes_email": "diaria",
        "tema": "automatico",
    }
    resp = api_client.patch(url, data)
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.frequencia_notificacoes_email == "diaria"
    assert admin_user.configuracao.tema == "automatico"
    assert admin_user.configuracao.receber_notificacoes_email is False


def test_get_preferences_includes_push(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert "receber_notificacoes_push" in data
    assert "frequencia_notificacoes_push" in data


def test_update_push_preferences(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("configuracoes_api:configuracoes-conta")
    data = {
        "receber_notificacoes_push": False,
        "frequencia_notificacoes_push": "diaria",
    }
    resp = api_client.patch(url, data)
    assert resp.status_code == 200
    admin_user.configuracao.refresh_from_db()
    assert admin_user.configuracao.receber_notificacoes_push is False
    assert admin_user.configuracao.frequencia_notificacoes_push == "diaria"


def test_requires_auth(api_client: APIClient):
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_only_owner_updates(api_client: APIClient):
    user1 = UserFactory()
    user2 = UserFactory()
    api_client.force_authenticate(user1)
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = api_client.patch(url, {"tema": "escuro"})
    assert resp.status_code == 200
    user2.configuracao.refresh_from_db()
    assert user2.configuracao.tema == "claro"


def test_response_time_p95(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    url = reverse("configuracoes_api:configuracoes-conta")
    timings: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        resp = api_client.get(url)
        assert resp.status_code == 200
        timings.append(time.perf_counter() - start)
    timings.sort()
    p95_index = int(len(timings) * 0.95) - 1
    p95 = timings[p95_index]
    assert p95 <= 0.2
