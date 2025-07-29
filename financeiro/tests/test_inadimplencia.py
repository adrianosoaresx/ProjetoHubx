import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.tasks.notificar_inadimplencia import notificar_inadimplencia
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_notificacao_task(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    user = UserFactory()
    conta = ContaAssociado.objects.create(user=user)
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now() - timezone.timedelta(days=10),
        data_vencimento=timezone.now() - timezone.timedelta(days=5),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    notificar_inadimplencia.delay()
    lanc.refresh_from_db()
    assert lanc.ultima_notificacao is not None


def test_inadimplencias_endpoint(api_client, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    user = UserFactory()
    api_client.force_authenticate(user=user)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = ContaAssociado.objects.create(user=user)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        data_vencimento=timezone.now() - timezone.timedelta(days=3),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    url = "/api/financeiro/inadimplencias/"
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.data[0]["dias_atraso"] >= 3
