import inspect

from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.serializers import AporteSerializer, LancamentoFinanceiroSerializer
from financeiro.tasks import gerar_cobrancas_mensais
from financeiro.tasks.importar_pagamentos import importar_pagamentos_async


def test_public_docstrings():
    objs = [
        CentroCusto,
        ContaAssociado,
        LancamentoFinanceiro,
        AporteSerializer,
        gerar_cobrancas_mensais,
        importar_pagamentos_async,
    ]
    for obj in objs:
        assert inspect.getdoc(obj), f"{obj} sem docstring"


def test_serializer_message_i18n():
    centro = CentroCusto.objects.create(nome="C", tipo=CentroCusto.Tipo.ORGANIZACAO)
    data = {
        "centro_custo": str(centro.id),
        "tipo": LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        "valor": "10",
        "data_lancamento": "2024-01-02T00:00:00Z",
        "data_vencimento": "2024-01-01T00:00:00Z",
        "status": LancamentoFinanceiro.Status.PENDENTE,
    }
    serializer = LancamentoFinanceiroSerializer(data=data)
    assert not serializer.is_valid()
    msg = serializer.errors.get("non_field_errors", [""])[0]
    assert "Vencimento" in msg
