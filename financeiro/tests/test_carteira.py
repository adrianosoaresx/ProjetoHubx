import pytest
from decimal import Decimal

from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import Carteira, CentroCusto
from organizacoes.factories import OrganizacaoFactory

pytestmark = [pytest.mark.django_db, pytest.mark.urls("financeiro.tests.urls_carteira")]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def centro_custo():
    organizacao = OrganizacaoFactory()
    return CentroCusto.objects.create(
        nome="Centro 1",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=organizacao,
    )


@pytest.fixture
def financeiro_user():
    return UserFactory(user_type=UserType.FINANCEIRO)


def test_carteira_unique_constraint(centro_custo):
    Carteira.objects.create(
        centro_custo=centro_custo,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    with pytest.raises(IntegrityError):
        Carteira.objects.create(
            centro_custo=centro_custo,
            nome="Operacional 2",
            tipo=Carteira.Tipo.OPERACIONAL,
        )


def test_carteira_api_create_and_list(api_client, centro_custo, financeiro_user):
    api_client.force_authenticate(financeiro_user)
    url = reverse("financeiro_api:carteira-list")
    response = api_client.post(
        url,
        {
            "centro_custo": str(centro_custo.id),
            "nome": "Carteira Operacional",
            "tipo": Carteira.Tipo.OPERACIONAL,
            "saldo": "999.00",
        },
    )
    assert response.status_code == 201
    assert response.data["saldo"] == "0.00"

    Carteira.objects.create(
        centro_custo=centro_custo,
        nome="Carteira Reserva",
        tipo=Carteira.Tipo.RESERVA,
    )

    response = api_client.get(url, {"tipo": Carteira.Tipo.OPERACIONAL})
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["nome"] == "Carteira Operacional"


def test_carteira_api_update_ignores_saldo(api_client, centro_custo, financeiro_user):
    carteira = Carteira.objects.create(
        centro_custo=centro_custo,
        nome="Carteira Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    api_client.force_authenticate(financeiro_user)
    url = reverse("financeiro_api:carteira-detail", args=[carteira.id])
    response = api_client.patch(url, {"nome": "Atualizada", "saldo": "100.00"})
    assert response.status_code == 200
    carteira.refresh_from_db()
    assert carteira.nome == "Atualizada"
    assert carteira.saldo == Decimal("0")
