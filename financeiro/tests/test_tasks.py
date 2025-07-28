import pytest

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.tasks import gerar_cobrancas_mensais
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
