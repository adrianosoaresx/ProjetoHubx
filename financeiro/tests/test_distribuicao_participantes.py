import pytest
from decimal import Decimal

import pytest

from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from financeiro.models import Carteira, CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.services.distribuicao import distribuir_receita_evento
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("somente_carteira", [True, False])
def test_repasse_para_participantes(settings, somente_carteira):
    settings.FINANCEIRO_SOMENTE_CARTEIRA = somente_carteira
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="N", tipo="nucleo", nucleo=nucleo)
    carteira_nucleo = Carteira.objects.create(
        centro_custo=centro_nucleo,
        nome="Carteira Núcleo",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    evento = EventoFactory(organizacao=org, nucleo=nucleo, status=0)

    pagante = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    p1 = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    p2 = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    carteira_p1 = Carteira.objects.create(
        conta_associado=p1,
        nome="Carteira P1",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_p2 = Carteira.objects.create(
        conta_associado=p2,
        nome="Carteira P2",
        tipo=Carteira.Tipo.OPERACIONAL,
    )

    distribuir_receita_evento(
        evento.id,
        Decimal("100"),
        pagante,
        participantes=[(p1, Decimal("30")), (p2, Decimal("70"))],
    )

    centro_nucleo.refresh_from_db()
    carteira_nucleo.refresh_from_db()
    carteira_p1.refresh_from_db()
    carteira_p2.refresh_from_db()
    p1.refresh_from_db()
    p2.refresh_from_db()

    assert carteira_nucleo.saldo == Decimal("0")
    assert carteira_p1.saldo == Decimal("30")
    assert carteira_p2.saldo == Decimal("70")
    assert centro_nucleo.saldo == Decimal("0")
    if somente_carteira:
        assert p1.saldo == Decimal("0")
        assert p2.saldo == Decimal("0")
    else:
        assert p1.saldo == Decimal("30")
        assert p2.saldo == Decimal("70")
    assert LancamentoFinanceiro.objects.filter(tipo="repasse", conta_associado=p1, valor=30).exists()
    assert LancamentoFinanceiro.objects.filter(tipo="repasse", conta_associado=p2, valor=70).exists()
