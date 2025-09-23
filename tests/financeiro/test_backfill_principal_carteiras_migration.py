from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_backfill_principal_carteiras_migration():
    executor = MigrationExecutor(connection)
    leaf_nodes = executor.loader.graph.leaf_nodes()
    migrate_from: list[tuple[str, str]] = []
    migrate_to: list[tuple[str, str]] = []
    for app_label, migration_name in leaf_nodes:
        if app_label == "financeiro":
            migrate_from.append(
                ("financeiro", "0013_carteira_conta_associado_alter_carteira_centro_custo_and_more")
            )
            migrate_to.append(("financeiro", "0014_backfill_principal_carteiras"))
        else:
            migrate_from.append((app_label, migration_name))
            migrate_to.append((app_label, migration_name))

    old_apps = executor.loader.project_state(migrate_from).apps
    executor.migrate(migrate_from)

    User = old_apps.get_model("accounts", "User")
    CentroCusto = old_apps.get_model("financeiro", "CentroCusto")
    ContaAssociado = old_apps.get_model("financeiro", "ContaAssociado")
    Lancamento = old_apps.get_model("financeiro", "LancamentoFinanceiro")

    user = User.objects.create(
        email="assoc@example.com",
        username="assoc",
        password="test",
        user_type="associado",
    )
    centro = CentroCusto.objects.create(
        nome="Centro Principal",
        tipo="organizacao",
        saldo=Decimal("150.00"),
    )
    conta = ContaAssociado.objects.create(user=user, saldo=Decimal("75.50"))
    lancamento = Lancamento.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo="mensalidade_associacao",
        valor=Decimal("10.00"),
    )

    centro_id = centro.id
    conta_id = conta.id
    lancamento_id = lancamento.id

    executor.loader.build_graph()
    executor.migrate(migrate_to)
    new_apps = executor.loader.project_state(migrate_to).apps

    Carteira = new_apps.get_model("financeiro", "Carteira")
    LancamentoFinanceiro = new_apps.get_model("financeiro", "LancamentoFinanceiro")

    centro_carteira = Carteira.objects.get(centro_custo_id=centro_id, tipo="operacional")
    assert centro_carteira.saldo == Decimal("150.00")
    assert centro_carteira.conta_associado_id is None

    conta_carteira = Carteira.objects.get(conta_associado_id=conta_id, tipo="operacional")
    assert conta_carteira.saldo == Decimal("75.50")
    assert conta_carteira.centro_custo_id is None

    lancamento_atualizado = LancamentoFinanceiro.objects.get(id=lancamento_id)
    assert lancamento_atualizado.carteira_id == centro_carteira.id
    assert lancamento_atualizado.carteira_contraparte_id == conta_carteira.id

    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
