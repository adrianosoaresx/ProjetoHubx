import pytest
from decimal import Decimal

from accounts.factories import UserFactory
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from financeiro.tasks import gerar_cobrancas_mensais
from financeiro.services import metrics
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_cobrancas_geradas_e_metricas(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    org = OrganizacaoFactory()
    centro_org = CentroCusto.objects.create(nome="Org", tipo="organizacao", organizacao=org)
    nucleo = NucleoFactory(organizacao=org, mensalidade=Decimal("25"))
    centro_nucleo = CentroCusto.objects.create(nome="N", tipo="nucleo", nucleo=nucleo)
    user = UserFactory(is_associado=True)
    conta = ContaAssociado.objects.create(user=user)
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, status="ativo")
    before = metrics.financeiro_cobrancas_total._value.get()
    gerar_cobrancas_mensais()
    assert (
        LancamentoFinanceiro.objects.filter(
            conta_associado=conta, tipo="mensalidade_associacao"
        ).count()
        == 1
    )
    assert LancamentoFinanceiro.objects.filter(
        centro_custo=centro_nucleo, tipo="mensalidade_nucleo", valor=nucleo.mensalidade
    ).exists()
    assert metrics.financeiro_cobrancas_total._value.get() == before + 2
    gerar_cobrancas_mensais()
    assert (
        LancamentoFinanceiro.objects.filter(
            conta_associado=conta, tipo="mensalidade_associacao"
        ).count()
        == 1
    )
