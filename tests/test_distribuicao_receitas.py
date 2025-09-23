import pytest
from decimal import Decimal

from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from financeiro.models import Carteira, CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.services.distribuicao import distribuir_receita_evento
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory


@pytest.mark.django_db
def test_distribuicao_para_nucleo():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="N", tipo="nucleo", nucleo=nucleo)
    carteira_nucleo = Carteira.objects.create(
        centro_custo=centro_nucleo,
        nome="Carteira Núcleo",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    conta = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    evento = EventoFactory(organizacao=org, nucleo=nucleo, status=0)
    distribuir_receita_evento(evento.id, Decimal("100"), conta)
    centro_nucleo.refresh_from_db()
    carteira_nucleo.refresh_from_db()
    assert carteira_nucleo.saldo == Decimal("100")
    assert centro_nucleo.saldo == Decimal("0")
    assert LancamentoFinanceiro.objects.filter(centro_custo=centro_nucleo, valor=100).exists()


@pytest.mark.django_db
def test_distribuicao_sem_nucleo():
    org = OrganizacaoFactory()
    centro_org = CentroCusto.objects.create(nome="Org", tipo="organizacao", organizacao=org)
    carteira_org = Carteira.objects.create(
        centro_custo=centro_org,
        nome="Carteira Org",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    evento = EventoFactory(organizacao=org, nucleo=None, status=0)
    centro_evento = CentroCusto.objects.create(nome="E", tipo="evento", evento=evento)
    carteira_evento = Carteira.objects.create(
        centro_custo=centro_evento,
        nome="Carteira Evento",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    conta = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    distribuir_receita_evento(evento.id, Decimal("80"), conta)
    centro_org.refresh_from_db()
    centro_evento.refresh_from_db()
    carteira_org.refresh_from_db()
    carteira_evento.refresh_from_db()
    assert carteira_org.saldo == Decimal("40")
    assert carteira_evento.saldo == Decimal("40")
    assert centro_org.saldo == Decimal("0")
    assert centro_evento.saldo == Decimal("0")
