import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.tasks import gerar_cobrancas_mensais
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def _setup_org_centro():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Org", tipo="organizacao", organizacao=org)
    return org, centro


def test_cobranca_associacao_para_todos(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    _, centro = _setup_org_centro()
    users = UserFactory.create_batch(3)
    for u in users:
        ContaAssociado.objects.create(user=u)
    gerar_cobrancas_mensais()
    assert LancamentoFinanceiro.objects.filter(tipo="mensalidade_associacao", centro_custo=centro).count() == 3


def test_cobranca_nucleo(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    org, centro_org = _setup_org_centro()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="N", tipo="nucleo", nucleo=nucleo)
    user = UserFactory()
    ContaAssociado.objects.create(user=user)
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, status="ativo")

    gerar_cobrancas_mensais()
    tipos = LancamentoFinanceiro.objects.values_list("tipo", flat=True)
    assert "mensalidade_associacao" in tipos
    assert "mensalidade_nucleo" in tipos
    assert LancamentoFinanceiro.objects.filter(centro_custo=centro_nucleo).exists()


def test_query_efficiency(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    _setup_org_centro()
    u1 = UserFactory()
    ContaAssociado.objects.create(user=u1)
    with CaptureQueriesContext(connection) as ctx:
        gerar_cobrancas_mensais()
    assert len(ctx) <= 5
