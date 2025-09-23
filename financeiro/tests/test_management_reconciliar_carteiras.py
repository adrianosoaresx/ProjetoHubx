from __future__ import annotations

import io
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from financeiro.models import Carteira, CentroCusto, LancamentoFinanceiro


@pytest.mark.django_db
def test_reconciliar_carteiras_sem_divergencia(tmp_path):
    User = get_user_model()
    usuario = User.objects.create_user(
        email="financeiro-teste@example.com",
        username="financeiro_teste",
        password="senha-secreta",
    )
    conta = usuario.contas_financeiras.create()
    centro = CentroCusto.objects.create(nome="Centro", tipo=CentroCusto.Tipo.ORGANIZACAO)

    carteira_centro = Carteira.objects.create(
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
        centro_custo=centro,
        saldo=Decimal("150.00"),
    )
    carteira_conta = Carteira.objects.create(
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
        conta_associado=conta,
        saldo=Decimal("150.00"),
    )

    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        carteira=carteira_centro,
        carteira_contraparte=carteira_conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=Decimal("200.00"),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        carteira=carteira_centro,
        carteira_contraparte=carteira_conta,
        tipo=LancamentoFinanceiro.Tipo.AJUSTE,
        valor=Decimal("-50.00"),
        status=LancamentoFinanceiro.Status.PAGO,
    )

    saida = io.StringIO()
    destino_csv = tmp_path / "reconciliacao.csv"
    call_command(
        "reconciliar_carteiras",
        stdout=saida,
        csv_path=str(destino_csv),
    )

    conteudo = saida.getvalue()
    assert "Nenhuma divergência encontrada." in conteudo
    assert "DIVERGENTE" not in conteudo
    csv_texto = destino_csv.read_text(encoding="utf-8")
    assert str(carteira_centro.id) in csv_texto
    assert "OK" in csv_texto


@pytest.mark.django_db
def test_reconciliar_carteiras_detecta_divergencia():
    User = get_user_model()
    usuario = User.objects.create_user(
        email="financeiro-divergente@example.com",
        username="financeiro_divergente",
        password="senha-secreta",
    )
    conta = usuario.contas_financeiras.create()
    centro = CentroCusto.objects.create(nome="Centro", tipo=CentroCusto.Tipo.ORGANIZACAO)

    carteira = Carteira.objects.create(
        nome="Carteira Divergente",
        tipo=Carteira.Tipo.OPERACIONAL,
        centro_custo=centro,
        saldo=Decimal("80.00"),
    )

    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        carteira=carteira,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=Decimal("50.00"),
        status=LancamentoFinanceiro.Status.PAGO,
    )

    saida = io.StringIO()
    erros = io.StringIO()
    with pytest.raises(CommandError):
        call_command("reconciliar_carteiras", stdout=saida, stderr=erros)

    linhas = saida.getvalue()
    assert "DIVERGENTE" in linhas
    assert str(carteira.id) in linhas
    assert "Divergências encontradas" in erros.getvalue()
