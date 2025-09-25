import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_create_centro(api_client):
    url = reverse("financeiro_api:centro-list")
    resp = api_client.post(url, {"nome": "Centro 1", "tipo": "organizacao"})
    assert resp.status_code == 401  # requires auth


@pytest.fixture
def user():
    return UserFactory()


def auth(client, user):
    client.force_authenticate(user=user)


def test_lancamentos_list_filtra_e_restringe(api_client, user):
    auth(api_client, user)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao", organizacao=org)
    conta_user = ContaAssociado.objects.create(user=user)
    outro = UserFactory()
    conta_outro = ContaAssociado.objects.create(user=outro)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta_user,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta_outro,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    url = reverse("financeiro_api:lancamento-list")
    resp = api_client.get(url, {"status": "pago"})
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["legacy_warning"] == ContaAssociado.LEGACY_MESSAGE
    assert "carteira_contraparte_id" in resp.data[0]
    assert "conta_associado" not in resp.data[0]


def test_associado_nao_pode_quitar(api_client, user):
    auth(api_client, user)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao", organizacao=org)
    conta_user = ContaAssociado.objects.create(user=user)
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta_user,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    url = reverse("financeiro_api:lancamento-detail", args=[lanc.id])
    resp = api_client.patch(url, {"status": "pago"})
    assert resp.status_code == 403
