import pytest
from decimal import Decimal

from accounts.factories import UserFactory
from financeiro.models import Carteira, CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.services.ajustes import ajustar_lancamento
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_ajuste_lancamento_pago():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org, saldo=Decimal("100"))
    user = UserFactory(is_associado=True)
    conta = ContaAssociado.objects.create(user=user, saldo=Decimal("100"))
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("100"),
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("100"),
    )
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        carteira=carteira_centro,
        carteira_contraparte=carteira_conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=Decimal("100"),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    ajustar_lancamento(lanc.id, Decimal("150"), "correcao", user)
    centro.refresh_from_db()
    conta.refresh_from_db()
    lanc.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert carteira_centro.saldo == Decimal("150")
    assert carteira_conta.saldo == Decimal("150")
    assert centro.saldo == Decimal("100")
    assert conta.saldo == Decimal("100")
    assert lanc.ajustado is True
    ajuste = LancamentoFinanceiro.objects.filter(lancamento_original=lanc).first()
    assert ajuste and ajuste.valor == Decimal("50")


@pytest.mark.django_db
def test_nao_ajusta_pendente():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory(is_associado=True)
    conta = ContaAssociado.objects.create(user=user)
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=Decimal("100"),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    with pytest.raises(Exception):
        ajustar_lancamento(lanc.id, Decimal("120"), "erro", user)
