import uuid

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_create_centro(api_client):
    url = reverse("financeiro_api:centro-list")
    resp = api_client.post(url, {"nome": "Centro 1", "tipo": "organizacao"})
    assert resp.status_code == 401  # requires auth


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="a@a.com", username="a", password="p")


def auth(client, user):
    client.force_authenticate(user=user)


def test_list_inadimplencias(api_client, user):
    auth(api_client, user)
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao")
    conta = ContaAssociado.objects.create(user_id=uuid.uuid4())
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo="mensalidade_associacao",
        valor=50,
        data_lancamento=timezone.now(),
        status="pendente",
    )
    url = reverse("financeiro_api:financeiro-inadimplencias")
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert len(resp.data) == 1
