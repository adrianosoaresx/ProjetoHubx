from decimal import Decimal

import pytest
from decimal import Decimal
from django.utils import timezone

from accounts.factories import UserFactory
from financeiro.models import Carteira, CentroCusto, ContaAssociado, FinanceiroLog, LancamentoFinanceiro
from financeiro.serializers import LancamentoFinanceiroSerializer
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("somente_carteira", [True, False])
def test_lancamento_atualiza_saldos(settings, somente_carteira):
    settings.FINANCEIRO_SOMENTE_CARTEIRA = somente_carteira
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
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
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert carteira_centro.saldo == Decimal("100")
    assert carteira_conta.saldo == Decimal("100")
    if somente_carteira:
        assert centro.saldo == Decimal("0")
        assert conta.saldo == Decimal("0")
    else:
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


def test_centro_custo_descricao():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Org",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=org,
        descricao="Descricao teste",
    )
    assert centro.descricao == "Descricao teste"


def test_lancamento_financeiro_carteira_campos_opcionais():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Org",
        tipo=CentroCusto.Tipo.ORGANIZACAO,
        organizacao=org,
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


def test_lancamento_financeiro_carteiras_serializer_read_only():
    serializer = LancamentoFinanceiroSerializer()
    assert "carteira" in serializer.fields
    assert serializer.fields["carteira"].read_only is True
    assert "carteira_contraparte" in serializer.fields
    assert serializer.fields["carteira_contraparte"].read_only is True
