import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_relatorios_query_count(api_client, django_assert_num_queries):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    centro = CentroCusto.objects.create(nome="C1", tipo="organizacao", organizacao=org)
    ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=10,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        status=LancamentoFinanceiro.Status.PAGO,
    )
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:financeiro-relatorios") + f"?centro={centro.id}"
    with django_assert_num_queries(5):
        resp = api_client.get(url)
    assert resp.status_code == 200
