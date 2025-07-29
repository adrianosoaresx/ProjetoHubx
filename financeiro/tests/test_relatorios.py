import pytest
from django.utils import timezone

from financeiro.models import CentroCusto, LancamentoFinanceiro
from financeiro.services.relatorios import gerar_relatorio
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_gera_serie_temporal(django_assert_num_queries):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=50,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=-20,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    with django_assert_num_queries(4):
        data = gerar_relatorio(centro=str(centro.id))
    assert data["saldo_atual"] == float(centro.saldo)
    assert data["serie"][0]["receitas"] == 50.0
    assert data["serie"][0]["despesas"] == 20.0
