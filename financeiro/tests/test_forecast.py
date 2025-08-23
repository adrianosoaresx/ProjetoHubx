import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework.reverse import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from financeiro.models import CentroCusto, LancamentoFinanceiro
import financeiro.viewsets as v

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return UserFactory(user_type=UserType.ADMIN)


def auth(client, user):
    client.force_authenticate(user=user)


def criar_series(centro, meses):
    for i in range(meses):
        dt = timezone.now() - timedelta(days=30 * (meses - i))
        LancamentoFinanceiro.objects.create(
            centro_custo=centro,
            tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            valor=100 + i,
            data_lancamento=dt,
            status=LancamentoFinanceiro.Status.PAGO,
        )
        LancamentoFinanceiro.objects.create(
            centro_custo=centro,
            tipo=LancamentoFinanceiro.Tipo.DESPESA,
            valor=-50 - i,
            data_lancamento=dt,
            status=LancamentoFinanceiro.Status.PAGO,
        )


def setup_centro():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao", organizacao=org)
    return centro


def test_previsao_series_longa(api_client, admin_user):
    auth(api_client, admin_user)
    centro = setup_centro()
    criar_series(centro, 12)
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "centro", "id": str(centro.id), "periodos": 2})
    assert resp.status_code == 200
    assert len(resp.data["previsao"]) == 2
    assert resp.data["historico"]


def test_previsao_series_curta(api_client, admin_user):
    auth(api_client, admin_user)
    centro = setup_centro()
    criar_series(centro, 3)
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "centro", "id": str(centro.id), "periodos": 2})
    assert resp.status_code == 200
    assert len(resp.data["previsao"]) == 2


def test_previsao_sem_dados(api_client, admin_user):
    auth(api_client, admin_user)
    centro = setup_centro()
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "centro", "id": str(centro.id), "periodos": 1})
    assert resp.status_code == 200
    assert resp.data["historico"] == []
    assert resp.data["previsao"][0]["receita"] == 0


def test_parametros_simulacao(api_client, admin_user):
    auth(api_client, admin_user)
    centro = setup_centro()
    criar_series(centro, 6)
    url = reverse("financeiro_api:forecast-list")
    base = api_client.get(url, {"escopo": "centro", "id": str(centro.id), "periodos": 1}).data["previsao"][0]
    ajust = api_client.get(
        url,
        {
            "escopo": "centro",
            "id": str(centro.id),
            "periodos": 1,
            "crescimento_receita": 10,
            "reducao_despesa": 10,
        },
    ).data["previsao"][0]
    assert ajust["receita"] > base["receita"]
    assert ajust["despesa"] < base["despesa"]


def test_cache(api_client, admin_user, monkeypatch):
    auth(api_client, admin_user)
    centro = setup_centro()
    criar_series(centro, 6)
    calls = []

    def fake(*args, **kwargs):
        calls.append(True)
        return {"historico": [], "previsao": []}

    monkeypatch.setattr(v, "calcular_previsao", fake)
    cache.clear()
    url = reverse("financeiro_api:forecast-list")
    params = {"escopo": "centro", "id": str(centro.id), "periodos": 1}
    api_client.get(url, params)
    api_client.get(url, params)
    assert len(calls) == 1


def test_forecast_organizacao_forbidden(api_client):
    org1 = OrganizacaoFactory()
    org2 = OrganizacaoFactory()
    nucleo1 = NucleoFactory(organizacao=org1)
    user = UserFactory(
        user_type=UserType.ADMIN, organizacao=org1, nucleo_obj=nucleo1
    )
    auth(api_client, user)
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "organizacao", "id": str(org2.id)})
    assert resp.status_code == 403


def test_forecast_nucleo_forbidden(api_client):
    org1 = OrganizacaoFactory()
    org2 = OrganizacaoFactory()
    nucleo1 = NucleoFactory(organizacao=org1)
    nucleo2 = NucleoFactory(organizacao=org2)
    user = UserFactory(
        user_type=UserType.ADMIN, organizacao=org1, nucleo_obj=nucleo1
    )
    auth(api_client, user)
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "nucleo", "id": str(nucleo2.id)})
    assert resp.status_code == 403


def test_forecast_centro_forbidden(api_client):
    org1 = OrganizacaoFactory()
    org2 = OrganizacaoFactory()
    nucleo1 = NucleoFactory(organizacao=org1)
    user = UserFactory(
        user_type=UserType.ADMIN, organizacao=org1, nucleo_obj=nucleo1
    )
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org2)
    auth(api_client, user)
    url = reverse("financeiro_api:forecast-list")
    resp = api_client.get(url, {"escopo": "centro", "id": str(centro.id)})
    assert resp.status_code == 403
