import uuid

import pytest

from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.tasks import gerar_cobrancas_mensais

pytestmark = pytest.mark.django_db


def test_gerar_cobrancas_mensais(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    CentroCusto.objects.create(nome="C", tipo="organizacao")
    ContaAssociado.objects.create(user_id=uuid.uuid4())
    gerar_cobrancas_mensais()
    assert LancamentoFinanceiro.objects.filter(status="pendente").exists()
