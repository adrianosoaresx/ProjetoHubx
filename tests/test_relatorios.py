import pytest
from decimal import Decimal
from django.utils import timezone

from financeiro.models import CentroCusto, LancamentoFinanceiro
from financeiro.services.relatorios import gerar_relatorio
from organizacoes.factories import OrganizacaoFactory


pytestmark = pytest.mark.django_db


def test_tipo_filter_relatorio():
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
        tipo=LancamentoFinanceiro.Tipo.DESPESA,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )

    data = gerar_relatorio(centro=str(centro.id), tipo="receitas")
    assert data["serie"][0]["despesas"] == 0.0

    data = gerar_relatorio(centro=str(centro.id), tipo="despesas")
    assert data["serie"][0]["receitas"] == 0.0


def test_status_filter_relatorio():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=100,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=50,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )

    data = gerar_relatorio(centro=str(centro.id), status=LancamentoFinanceiro.Status.PAGO)
    assert data["serie"][0]["receitas"] == 50.0

    data = gerar_relatorio(centro=str(centro.id), status=LancamentoFinanceiro.Status.PENDENTE)
    assert data["serie"][0]["receitas"] == 100.0


def test_relatorio_inclui_saldos_por_centro(monkeypatch):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=100,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=-30,
        tipo=LancamentoFinanceiro.Tipo.DESPESA,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )

    def fake_saldos_por_centro(*_, **__):
        return {str(centro.id): Decimal("70")}

    monkeypatch.setattr(
        "financeiro.services.relatorios.saldos_carteiras_por_centro",
        fake_saldos_por_centro,
    )

    data = gerar_relatorio(centro=str(centro.id))

    assert data["saldos_por_centro"] == {str(centro.id): 70.0}
    assert data["saldo_atual"] == 70.0
