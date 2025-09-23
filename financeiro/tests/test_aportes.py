import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import (
    Carteira,
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    LancamentoFinanceiro,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _override_urls(settings):
    settings.ROOT_URLCONF = "tests.financeiro_api_urls"


@pytest.fixture
def admin_user():
    return UserFactory(user_type=UserType.ADMIN)


def auth(client: APIClient, user):
    client.force_authenticate(user=user)


def _create_centro(user) -> CentroCusto:
    org = getattr(user, "organizacao", None)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    Carteira.objects.create(
        centro_custo=centro,
        nome="Carteira Centro",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    return centro


def test_valor_negativo(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "-5",
            "descricao": "x",
        },
    )
    assert resp.status_code == 400


def test_tipo_invalido(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
            "tipo": "outro",
        },
    )
    assert resp.status_code == 400


def test_valor_zero_valido(api_client, admin_user):
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "0",
            "descricao": "x",
        },
    )
    assert resp.status_code == 201, resp.data


@pytest.mark.parametrize("somente_carteira", [True, False])
def test_aporte_interno_registra_originador(api_client, admin_user, settings, somente_carteira):
    settings.FINANCEIRO_SOMENTE_CARTEIRA = somente_carteira
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
        },
    )
    assert resp.status_code == 201, resp.data
    lanc = LancamentoFinanceiro.objects.get(pk=resp.data["id"])
    assert lanc.originador_id == admin_user.id
    centro.refresh_from_db()
    carteira = Carteira.objects.get(centro_custo=centro)
    carteira.refresh_from_db()
    assert carteira.saldo == Decimal("10")
    if somente_carteira:
        assert centro.saldo == 0
    else:
        assert centro.saldo == lanc.valor


def test_aporte_interno_sem_permissao(api_client):
    user = UserFactory()
    auth(api_client, user)
    centro = _create_centro(user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "10",
            "descricao": "x",
        },
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("somente_carteira", [True, False])
def test_aporte_externo(api_client, settings, somente_carteira):
    settings.FINANCEIRO_SOMENTE_CARTEIRA = somente_carteira
    user = UserFactory()
    auth(api_client, user)
    centro = _create_centro(user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "5",
            "descricao": "x",
            "tipo": "aporte_externo",
            "patrocinador": "Empresa X",
        },
    )
    assert resp.status_code == 201
    centro.refresh_from_db()
    carteira = Carteira.objects.get(centro_custo=centro)
    carteira.refresh_from_db()
    assert carteira.saldo == Decimal("5")
    if somente_carteira:
        assert centro.saldo == 0
    else:
        assert centro.saldo == 5


def test_aporte_retorna_recibo(api_client, admin_user, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    sent = {}

    def fake_send_email(user, subject, body):
        sent["user"] = user
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("financeiro.views.api.send_email", fake_send_email)
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {"centro_custo": str(centro.id), "valor": "10", "descricao": "x"},
    )
    assert resp.status_code == 201, resp.data
    assert "recibo_url" in resp.data
    file_path = tmp_path / "recibos" / f"aporte_{resp.data['id']}.html"
    assert file_path.exists()
    assert sent["user"] == admin_user
    assert str(resp.data["recibo_url"]) in sent["body"]


@pytest.mark.parametrize("somente_carteira", [True, False])
def test_estornar_aporte(api_client, admin_user, settings, somente_carteira):
    settings.FINANCEIRO_SOMENTE_CARTEIRA = somente_carteira
    auth(api_client, admin_user)
    centro = _create_centro(admin_user)
    carteira_centro = Carteira.objects.get(centro_custo=centro)
    associado = UserFactory(user_type=UserType.ASSOCIADO)
    conta = ContaAssociado.objects.create(user=associado)
    carteira_conta = Carteira.objects.create(
        conta_associado=conta,
        nome="Carteira Conta",
        tipo=Carteira.Tipo.OPERACIONAL,
    )
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "conta_associado": str(conta.id),
            "valor": "10",
            "descricao": "x",
        },
    )
    assert resp.status_code == 201
    aporte_id = resp.data["id"]
    centro.refresh_from_db()
    conta.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    assert carteira_centro.saldo == Decimal("10")
    assert carteira_conta.saldo == Decimal("10")
    if somente_carteira:
        assert centro.saldo == 0
        assert conta.saldo == 0
    else:
        assert centro.saldo == 10
        assert conta.saldo == 10

    estorno_url = reverse("financeiro_api:financeiro-estornar-aporte", args=[aporte_id])
    resp = api_client.post(estorno_url)
    assert resp.status_code == 200, resp.data
    centro.refresh_from_db()
    conta.refresh_from_db()
    carteira_centro.refresh_from_db()
    carteira_conta.refresh_from_db()
    lanc = LancamentoFinanceiro.objects.get(pk=aporte_id)
    assert lanc.status == LancamentoFinanceiro.Status.CANCELADO
    assert carteira_centro.saldo == Decimal("0")
    assert carteira_conta.saldo == Decimal("0")
    if somente_carteira:
        assert centro.saldo == 0
        assert conta.saldo == 0
    else:
        assert centro.saldo == 0
        assert conta.saldo == 0
    assert FinanceiroLog.objects.filter(dados_novos__id=aporte_id).exists()


def test_estornar_aporte_sem_permissao(api_client):
    admin = UserFactory(user_type=UserType.ADMIN)
    auth(api_client, admin)
    centro = _create_centro(admin)
    url = reverse("financeiro_api:financeiro-aportes")
    resp = api_client.post(
        url,
        {
            "centro_custo": str(centro.id),
            "valor": "5",
            "descricao": "x",
        },
    )
    aporte_id = resp.data["id"]

    user = UserFactory()
    auth(api_client, user)
    estorno_url = reverse("financeiro_api:financeiro-estornar-aporte", args=[aporte_id])
    resp = api_client.post(estorno_url)
    assert resp.status_code == 403
