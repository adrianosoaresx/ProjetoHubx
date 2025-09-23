from decimal import Decimal

import pytest

from financeiro.models import Carteira, CentroCusto, LancamentoFinanceiro
from financeiro.reporting import (
    saldos_carteiras_por_centro,
    saldos_lancamentos_por_centro,
    saldos_materializados_por_centro,
)
from organizacoes.factories import OrganizacaoFactory


pytestmark = pytest.mark.django_db


def criar_centro(nome: str = "Centro") -> CentroCusto:
    org = OrganizacaoFactory()
    return CentroCusto.objects.create(nome=nome, tipo="organizacao", organizacao=org)


def test_saldos_materializados_por_centro_com_carteiras():
    centro_a = criar_centro("A")
    centro_b = criar_centro("B")
    Carteira.objects.create(
        centro_custo=centro_a,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("25.00"),
    )
    Carteira.objects.create(
        centro_custo=centro_b,
        nome="Reserva",
        tipo=Carteira.Tipo.RESERVA,
        saldo=Decimal("10.00"),
    )

    saldos = saldos_materializados_por_centro(centro=[str(centro_a.id), str(centro_b.id)])

    assert saldos[str(centro_a.id)] == Decimal("25.00")
    assert saldos[str(centro_b.id)] == Decimal("10.00")


def test_saldos_lancamentos_por_centro_filtra_por_pago():
    centro = criar_centro("Lancamentos")
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=Decimal("30.00"),
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=Decimal("-5.00"),
        tipo=LancamentoFinanceiro.Tipo.DESPESA,
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=Decimal("-100.00"),
        tipo=LancamentoFinanceiro.Tipo.DESPESA,
        status=LancamentoFinanceiro.Status.PENDENTE,
    )

    saldos = saldos_lancamentos_por_centro(centro=str(centro.id))

    assert saldos[str(centro.id)] == Decimal("25.00")


def test_saldos_carteiras_por_centro_faz_fallback_para_lancamentos():
    centro = criar_centro("Fallback")
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=Decimal("100.00"),
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        status=LancamentoFinanceiro.Status.PAGO,
    )

    saldos = saldos_carteiras_por_centro(centro=str(centro.id))

    assert saldos[str(centro.id)] == Decimal("100.00")


def test_saldos_carteiras_por_centro_respeita_preferencia_sem_fallback():
    centro = criar_centro("Preferencia")
    Carteira.objects.create(
        centro_custo=centro,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("15.00"),
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=Decimal("40.00"),
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        status=LancamentoFinanceiro.Status.PAGO,
    )

    saldos = saldos_carteiras_por_centro(
        centro=str(centro.id),
        prefer_materializado=True,
        fallback_to_lancamentos=False,
    )

    assert saldos[str(centro.id)] == Decimal("15.00")


def test_saldos_carteiras_por_centro_inclui_centros_sem_movimentacao():
    centro_a = criar_centro("SemMov")
    centro_b = criar_centro("ComSaldo")
    Carteira.objects.create(
        centro_custo=centro_b,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("7.00"),
    )

    saldos = saldos_carteiras_por_centro(centro=[str(centro_a.id), str(centro_b.id)])

    assert saldos[str(centro_a.id)] == Decimal("0")
    assert saldos[str(centro_b.id)] == Decimal("7.00")
