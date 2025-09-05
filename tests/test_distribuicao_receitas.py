import pytest
from decimal import Decimal

from accounts.factories import UserFactory
from eventos.factories import EventoFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.services.distribuicao import distribuir_receita_evento
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory


@pytest.mark.django_db
def test_distribuicao_para_nucleo():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="N", tipo="nucleo", nucleo=nucleo)
    conta = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    evento = EventoFactory(organizacao=org, nucleo=nucleo, status=0)
    distribuir_receita_evento(evento.id, Decimal("100"), conta)
    centro_nucleo.refresh_from_db()
    assert centro_nucleo.saldo == Decimal("100")
    assert LancamentoFinanceiro.objects.filter(centro_custo=centro_nucleo, valor=100).exists()


@pytest.mark.django_db
def test_distribuicao_sem_nucleo():
    org = OrganizacaoFactory()
    centro_org = CentroCusto.objects.create(nome="Org", tipo="organizacao", organizacao=org)
    evento = EventoFactory(organizacao=org, nucleo=None, status=0)
    centro_evento = CentroCusto.objects.create(nome="E", tipo="evento", evento=evento)
    conta = ContaAssociado.objects.create(user=UserFactory(is_associado=True))
    distribuir_receita_evento(evento.id, Decimal("80"), conta)
    centro_org.refresh_from_db(); centro_evento.refresh_from_db()
    assert centro_org.saldo == Decimal("40")
    assert centro_evento.saldo == Decimal("40")
