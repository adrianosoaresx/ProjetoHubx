from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from financeiro.models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    IntegracaoConfig,
    LancamentoFinanceiro,
)
from financeiro.serializers import LancamentoFinanceiroSerializer
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_lancamento_atualiza_saldos():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    serializer = LancamentoFinanceiroSerializer(
        data={
            "centro_custo": str(centro.id),
            "conta_associado": str(conta.id),
            "tipo": LancamentoFinanceiro.Tipo.APORTE_INTERNO,
            "valor": "100",
            "data_lancamento": timezone.now(),
            "status": LancamentoFinanceiro.Status.PAGO,
            "descricao": "teste",
        }
    )
    assert serializer.is_valid(), serializer.errors
    lanc = serializer.save()
    centro.refresh_from_db()
    conta.refresh_from_db()
    assert centro.saldo == lanc.valor
    assert conta.saldo == lanc.valor


def test_contaassociado_str():
    user = UserFactory(email="teste@example.com")
    conta = ContaAssociado.objects.create(user=user, saldo=10)
    assert str(conta) == "teste@example.com (saldo: 10)"


def test_lancamento_default_vencimento():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Org",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=org,
    )
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        valor=Decimal("10"),
        data_lancamento=timezone.now(),
    )
    assert lanc.data_vencimento == lanc.data_lancamento
    assert lanc.origem == LancamentoFinanceiro.Origem.MANUAL


def test_serializer_vencimento_anterior_lancamento_error():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    data_lanc = timezone.now()
    data_venc = data_lanc - timezone.timedelta(days=1)
    serializer = LancamentoFinanceiroSerializer(
        data={
            "centro_custo": str(centro.id),
            "tipo": LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            "valor": "50",
            "data_lancamento": data_lanc,
            "data_vencimento": data_venc,
            "status": LancamentoFinanceiro.Status.PENDENTE,
        }
    )
    assert not serializer.is_valid()
    assert "Vencimento" in str(serializer.errors)


def test_financeirolog_str():
    user = UserFactory(email="log@example.com")
    log = FinanceiroLog.objects.create(
        usuario=user, acao=FinanceiroLog.Acao.IMPORTAR, dados_anteriores={}, dados_novos={}
    )
    assert "Importar Pagamentos" in str(log)
    assert "log@example.com" in str(log)


def test_lancamento_despesa_negativo():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    serializer = LancamentoFinanceiroSerializer(
        data={
            "centro_custo": str(centro.id),
            "conta_associado": str(conta.id),
            "tipo": LancamentoFinanceiro.Tipo.DESPESA,
            "valor": "-30",
            "data_lancamento": timezone.now(),
            "status": LancamentoFinanceiro.Status.PAGO,
        }
    )
    assert serializer.is_valid(), serializer.errors
    lanc = serializer.save()
    assert lanc.valor == Decimal("-30")


def test_lancamento_negativo_outro_tipo():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    serializer = LancamentoFinanceiroSerializer(
        data={
            "centro_custo": str(centro.id),
            "tipo": LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
            "valor": "-10",
            "data_lancamento": timezone.now(),
            "status": LancamentoFinanceiro.Status.PENDENTE,
        }
    )
    assert not serializer.is_valid()
    assert "Valor negativo" in str(serializer.errors)


def test_integracao_config_soft_delete():
    config = IntegracaoConfig.objects.create(
        nome="ERP Hub",
        tipo=IntegracaoConfig.Tipo.ERP,
        base_url="https://example.com",
    )
    config.soft_delete()
    config.refresh_from_db()
    assert config.deleted is True
    assert IntegracaoConfig.objects.count() == 0
    assert IntegracaoConfig.all_objects.count() == 1
