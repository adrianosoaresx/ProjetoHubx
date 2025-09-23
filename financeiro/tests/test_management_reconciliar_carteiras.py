from __future__ import annotations

import csv
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
    carteira_reserva = Carteira.objects.create(
        nome="Carteira Reserva",
        tipo=Carteira.Tipo.RESERVA,
        conta_associado=conta,
        saldo=Decimal("0.00"),
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
    assert "Resumo por tipo de carteira:" in conteudo
    assert "Detalhes por carteira:" in conteudo
    assert conteudo.index("Resumo por tipo de carteira:") < conteudo.index(
        "Detalhes por carteira:"
    )
    assert "Operacional (operacional)" in conteudo
    assert "Reserva (reserva)" in conteudo
    assert "Nenhuma divergência encontrada." in conteudo
    assert "DIVERGENTE" not in conteudo
    with destino_csv.open(newline="", encoding="utf-8") as arquivo_csv:
        linhas_csv = list(csv.reader(arquivo_csv))

    assert linhas_csv[0] == [
        "tipo",
        "tipo_rotulo",
        "quantidade_carteiras",
        "saldo_registrado",
        "saldo_calculado",
        "diferenca",
        "status",
    ]

    indice = 1
    resumo_linhas: list[list[str]] = []
    while indice < len(linhas_csv) and linhas_csv[indice]:
        resumo_linhas.append(linhas_csv[indice])
        indice += 1

    assert resumo_linhas, "Era esperado pelo menos um resumo por tipo"
    resumo_por_tipo = {linha[0]: linha for linha in resumo_linhas}

    resumo_operacional = resumo_por_tipo[Carteira.Tipo.OPERACIONAL]
    assert resumo_operacional[2] == "2"
    assert resumo_operacional[3] == "300.00"
    assert resumo_operacional[4] == "300.00"
    assert resumo_operacional[6] == "OK"

    resumo_reserva = resumo_por_tipo[Carteira.Tipo.RESERVA]
    assert resumo_reserva[2] == "1"
    assert resumo_reserva[3] == "0.00"
    assert resumo_reserva[4] == "0.00"
    assert resumo_reserva[6] == "OK"

    assert linhas_csv[indice] == []
    indice += 1

    assert linhas_csv[indice] == [
        "id",
        "nome",
        "tipo",
        "tipo_rotulo",
        "centro_custo_id",
        "conta_associado_id",
        "saldo_registrado",
        "saldo_calculado",
        "diferenca",
        "status",
    ]

    detalhes = linhas_csv[indice + 1 :]
    assert any(linha[0] == str(carteira_centro.id) for linha in detalhes)
    assert any(linha[0] == str(carteira_conta.id) for linha in detalhes)
    assert any(linha[0] == str(carteira_reserva.id) for linha in detalhes)
    assert all(linha[-1] == "OK" for linha in detalhes)


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
    assert "Resumo por tipo de carteira:" in linhas
    assert "Detalhes por carteira:" in linhas
    assert "DIVERGENTE" in linhas
    assert str(carteira.id) in linhas
    assert "Divergências encontradas" in erros.getvalue()
