import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, LancamentoFinanceiro

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return UserFactory(user_type=UserType.ADMIN)


def auth(client: APIClient, user):
    client.force_authenticate(user=user)


def _create_centro(user) -> CentroCusto:
    org = getattr(user, "organizacao", None)
    return CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)


def test_valor_invalido(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "0",
            "descricao": "x",
        },
    )
    assert resp.status_code == 400


def test_tipo_invalido(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
            "tipo": "outro",
        },
    )
    assert resp.status_code == 400


def test_aporte_interno_registra_originador(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
        },
    )
    assert resp.status_code == 201, resp.data
    lanc = LancamentoFinanceiro.objects.get(pk=resp.data["id"])
    assert lanc.originador_id == admin_user.id
    centro.refresh_from_db()
    assert centro.saldo == lanc.valor


def test_aporte_interno_sem_permissao(api_client):
    user = UserFactory()
    auth(api_client, user)
    centro = _create_centro(user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
        },
    )
    assert resp.status_code == 403


def test_aporte_externo(api_client):
    user = UserFactory()
    auth(api_client, user)
    centro = _create_centro(user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "5",
            "descricao": "x",
            "tipo": "aporte_externo",
            "patrocinador": "Empresa X",
        },
    )
    assert resp.status_code == 201
    centro.refresh_from_db()
    assert centro.saldo == 5

