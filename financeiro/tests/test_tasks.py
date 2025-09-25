import pytest

from accounts.factories import UserFactory
from financeiro.models import (
    CentroCusto,
    ContaAssociado,
    LancamentoFinanceiro,
    ImportacaoPagamentos,
)
from financeiro.tasks import gerar_cobrancas_mensais
from financeiro.tasks.importar_pagamentos import importar_pagamentos_async
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_gerar_cobrancas_mensais(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    org = OrganizacaoFactory()
    CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory(is_associado=True)
    ContaAssociado.objects.create(user=user)
    gerar_cobrancas_mensais()
    assert LancamentoFinanceiro.objects.filter(status="pendente").exists()


def test_importar_pagamentos_async_log(monkeypatch, tmp_path):
    user = UserFactory()
    csv_path = tmp_path / "pag.csv"
    csv_path.write_text("header\n", encoding="utf-8")
    importacao = ImportacaoPagamentos.objects.create(arquivo="pag.csv")

    def fake_process(self):
        return 0, []

    monkeypatch.setattr(
        "financeiro.tasks.importar_pagamentos.ImportadorPagamentos.process",
        fake_process,
    )
    monkeypatch.setattr(
        "financeiro.tasks.importar_pagamentos.enviar_para_usuario",
        lambda *a, **k: None,
    )

    importar_pagamentos_async(str(csv_path), str(user.id), str(importacao.id))
