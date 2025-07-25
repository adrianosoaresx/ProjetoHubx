from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


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


def test_requires_auth(api_client: APIClient):
    url = reverse("configuracoes_api:configuracoes-conta")
    resp = api_client.get(url)
    assert resp.status_code == 403
