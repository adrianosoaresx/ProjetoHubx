from __future__ import annotations

import csv

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from dashboard.utils import get_variation
from discussao.models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao
from feed.factories import PostFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _auth(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def test_get_variation_function() -> None:
    assert get_variation(100, 150) == 50
    assert get_variation(0, 50) == 5000


def test_export_csv(api_client: APIClient, admin_user) -> None:
    _auth(api_client, admin_user)
    url = reverse("dashboard_api:dashboard-export") + "?formato=csv"
    resp = api_client.get(url)
    assert resp.status_code == 200
    rows = list(csv.reader(resp.content.decode().splitlines()))
    assert rows[0] == ["Métrica", "Total", "Crescimento"]


def test_export_pdf(api_client: APIClient, admin_user, monkeypatch) -> None:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        pytest.skip("weasyprint não instalado")
    _auth(api_client, admin_user)
    monkeypatch.setattr("weasyprint.HTML.write_pdf", lambda self: b"pdf")
    url = reverse("dashboard_api:dashboard-export") + "?formato=pdf"
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"


def test_filter_crud(api_client: APIClient, admin_user) -> None:
    _auth(api_client, admin_user)
    url = reverse("dashboard_api:dashboard-filter-list")
    resp = api_client.post(
        url,
        {"nome": "f1", "filtros": {"periodo": "mensal"}},
        format="json",
    )
    assert resp.status_code == 201
    filtro_id = resp.data["id"]

    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.data[0]["id"] == filtro_id

    url_dashboard = reverse("dashboard_api:dashboard-list") + f"?filter_id={filtro_id}"
    resp = api_client.get(url_dashboard)
    assert resp.status_code == 200


def test_dashboard_permission_error(api_client: APIClient, cliente_user, admin_user) -> None:
    _auth(api_client, cliente_user)
    url = reverse("dashboard_api:dashboard-list") + f"?escopo=organizacao&organizacao_id={admin_user.organizacao_id}"
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_dashboard_invalid_param(api_client: APIClient, admin_user) -> None:
    _auth(api_client, admin_user)
    url = reverse("dashboard_api:dashboard-list") + "?periodo=foo"
    resp = api_client.get(url)
    assert resp.status_code == 400


def test_metrics_cache(api_client: APIClient, admin_user, monkeypatch) -> None:
    calls = {"c": 0}

    def fake(*args, **kwargs):
        calls["c"] += 1
        return {"total": 0, "crescimento": 0.0}

    monkeypatch.setattr("dashboard.services.DashboardService.calcular_crescimento", fake)
    _auth(api_client, admin_user)
    url = reverse("dashboard_api:dashboard-list")
    api_client.get(url)
    api_client.get(url)
    assert calls["c"] == 10


def test_dashboard_new_metrics(api_client: APIClient, admin_user) -> None:
    _auth(api_client, admin_user)
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    cat = CategoriaDiscussao.objects.create(nome="c", slug="c", organizacao=admin_user.organizacao)
    topico = TopicoDiscussao.objects.create(
        categoria=cat, titulo="t", slug="t", conteudo="x", autor=admin_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="r")
    url = (
        reverse("dashboard_api:dashboard-list")
        + "?metricas=num_posts_feed_total&metricas=num_posts_feed_recent&metricas=num_topicos&metricas=num_respostas"
        + f"&escopo=organizacao&organizacao_id={admin_user.organizacao_id}"
    )
    resp = api_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["num_posts_feed_total"]["total"] == 1
    assert data["num_posts_feed_recent"]["total"] == 1
    assert data["num_topicos"]["total"] == 1
    assert data["num_respostas"]["total"] == 1
