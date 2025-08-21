import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from agenda.factories import EventoFactory
from financeiro.models import CentroCusto, LancamentoFinanceiro, FinanceiroLog
from financeiro.serializers import LancamentoFinanceiroSerializer
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_root_sem_acesso(api_client):
    user = UserFactory(user_type=UserType.ROOT)
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:centro-list")
    resp = api_client.get(url)
    assert resp.status_code == 403


def test_quitar_lancamento(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = admin.contas_financeiras.create()
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    url = reverse("financeiro_api:lancamento-detail", args=[lanc.id])
    resp = api_client.patch(url, {"status": "pago"})
    assert resp.status_code == 200
    lanc.refresh_from_db()
    centro.refresh_from_db()
    conta.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.PAGO
    assert centro.saldo == 50
    assert conta.saldo == 50


def test_pagar_endpoint(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = admin.contas_financeiras.create()
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    url = reverse("financeiro_api:lancamento-pagar", args=[lanc.id])
    resp = api_client.post(url)
    assert resp.status_code == 200
    lanc.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.PAGO
    assert FinanceiroLog.objects.filter(acao=FinanceiroLog.Acao.EDITAR_LANCAMENTO, dados_novos__id=str(lanc.id)).exists()


def test_distribuicao_ingresso():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="CN", tipo="nucleo", nucleo=nucleo)
    evento = EventoFactory(organizacao=org, nucleo=nucleo)
    centro_evento = CentroCusto.objects.create(nome="CE", tipo="evento", evento=evento, nucleo=nucleo)
    payload = {
        "centro_custo": str(centro_evento.id),
        "tipo": "ingresso_evento",
        "valor": "25",
        "data_lancamento": timezone.now().isoformat(),
        "status": "pago",
    }
    serializer = LancamentoFinanceiroSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    assert CentroCusto.objects.get(id=centro_nucleo.id).saldo == 25
    assert LancamentoFinanceiro.objects.filter(descricao="Repasse de ingresso", centro_custo=centro_nucleo).exists()
