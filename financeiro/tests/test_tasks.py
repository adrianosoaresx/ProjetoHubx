import pytest

from accounts.factories import UserFactory
from financeiro.models import (
    CentroCusto,
    ContaAssociado,
    LancamentoFinanceiro,
    FinanceiroTaskLog,
)
from financeiro.tasks import gerar_cobrancas_mensais
from financeiro.tasks.importar_pagamentos import importar_pagamentos_async
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_gerar_cobrancas_mensais(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    org = OrganizacaoFactory()
    CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory()
    ContaAssociado.objects.create(user=user)
    gerar_cobrancas_mensais()
    assert LancamentoFinanceiro.objects.filter(status="pendente").exists()
    assert FinanceiroTaskLog.objects.filter(
        nome_tarefa="gerar_cobrancas_mensais", status="sucesso"
    ).exists()


def test_importar_pagamentos_async_log(monkeypatch, tmp_path):
    user = UserFactory()
    csv_path = tmp_path / "pag.csv"
    csv_path.write_text("header\n", encoding="utf-8")

    def fake_process(self):
        return 0, []

    monkeypatch.setattr(
        "financeiro.tasks.importar_pagamentos.ImportadorPagamentos.process",
        fake_process,
    )

    importar_pagamentos_async(str(csv_path), str(user.id))
    assert FinanceiroTaskLog.objects.filter(
        nome_tarefa="importar_pagamentos_async", status="sucesso"
    ).exists()
