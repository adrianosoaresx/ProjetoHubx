import pytest
from decimal import Decimal
from django.utils import timezone

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from financeiro.models import Carteira, CentroCusto, ContaAssociado, LancamentoFinanceiro


pytestmark = pytest.mark.django_db


def test_contaassociado_str():
    user = UserFactory(email="teste@example.com")
    conta = ContaAssociado.objects.create(user=user, saldo=Decimal("10"))
    assert str(conta) == "teste@example.com (saldo: 10)"


def test_lancamento_default_vencimento_e_origem():
    organizacao = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Org",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=organizacao,
    )
    lancamento = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        valor=Decimal("10"),
        data_lancamento=timezone.now(),
    )
    assert lancamento.data_vencimento == lancamento.data_lancamento
    assert lancamento.origem == LancamentoFinanceiro.Origem.MANUAL


def test_lancamento_campos_carteira_opcionais():
    organizacao = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Org",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=organizacao,
    )
    carteira = Carteira.objects.create(
        centro_custo=centro,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
    )

    lancamento = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        valor=Decimal("1"),
        data_lancamento=timezone.now(),
        carteira=carteira,
    )

    assert lancamento.carteira == carteira

    lancamento.carteira = None
    lancamento.carteira_contraparte = None
    lancamento.save(update_fields=["carteira", "carteira_contraparte"])
    lancamento.refresh_from_db()

    carteira_field = LancamentoFinanceiro._meta.get_field("carteira")
    contraparte_field = LancamentoFinanceiro._meta.get_field("carteira_contraparte")

    assert lancamento.carteira is None
    assert lancamento.carteira_contraparte is None
    assert carteira_field.null is True
    assert carteira_field.blank is True
    assert contraparte_field.null is True
    assert contraparte_field.blank is True
