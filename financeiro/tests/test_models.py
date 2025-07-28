from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
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
