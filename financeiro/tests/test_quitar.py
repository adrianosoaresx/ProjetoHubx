import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from eventos.factories import EventoFactory
from financeiro.models import Carteira, CentroCusto, LancamentoFinanceiro
from financeiro.serializers import LancamentoFinanceiroSerializer
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _override_urls(settings):
    settings.ROOT_URLCONF = "tests.financeiro_api_urls"


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
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        carteira=carteira_centro,
        carteira_contraparte=carteira_conta,
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
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.PAGO
    assert carteira_centro.saldo == Decimal("50")
    assert carteira_conta.saldo == Decimal("50")
    assert conta.saldo == 0
def test_pagar_endpoint(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = admin.contas_financeiras.create()
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
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
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.PAGO
    assert lanc.carteira_id == carteira_centro.id
    assert lanc.carteira_contraparte_id == carteira_conta.id
    assert carteira_centro.saldo == Decimal("50")
    assert carteira_conta.saldo == Decimal("50")
def test_pagar_endpoint_idempotente(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = admin.contas_financeiras.create()
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    url = reverse("financeiro_api:lancamento-pagar", args=[lanc.id])
    first = api_client.post(url)
    assert first.status_code == 200
    segundo = api_client.post(url)
    assert segundo.status_code == 400
    assert segundo.json()["detail"] == "Lançamento já está pago"
    lanc.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.PAGO
    assert carteira_centro.saldo == Decimal("50")
    assert carteira_conta.saldo == Decimal("50")
def test_pagar_cancelado_bloqueado(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=admin)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    conta = admin.contas_financeiras.create()
    carteira_centro = Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    lanc = LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.CANCELADO,
    )
    url = reverse("financeiro_api:lancamento-pagar", args=[lanc.id])
    resp = api_client.post(url)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Lançamentos cancelados não podem ser pagos"
    lanc.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert lanc.status == LancamentoFinanceiro.Status.CANCELADO
    assert carteira_centro.saldo == Decimal("0")
    assert carteira_conta.saldo == Decimal("0")
def test_distribuicao_ingresso():
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro_nucleo = CentroCusto.objects.create(nome="CN", tipo="nucleo", nucleo=nucleo)
    evento = EventoFactory(organizacao=org, nucleo=nucleo)
    centro_evento = CentroCusto.objects.create(nome="CE", tipo="evento", evento=evento, nucleo=nucleo)
    carteira_nucleo = Carteira.objects.create(
        centro_custo=centro_nucleo,
        nome="Carteira Núcleo",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    Carteira.objects.create(
        centro_custo=centro_evento,
        nome="Carteira Evento",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
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
    carteira_nucleo.refresh_from_db()
    assert carteira_nucleo.saldo == Decimal("25")
    assert LancamentoFinanceiro.objects.filter(descricao="Repasse de ingresso", centro_custo=centro_nucleo).exists()
