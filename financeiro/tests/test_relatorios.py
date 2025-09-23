import csv
from decimal import Decimal

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import Carteira, CentroCusto, LancamentoFinanceiro
from financeiro.services.relatorios import gerar_relatorio
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_gera_serie_temporal(django_assert_num_queries):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    Carteira.objects.create(
        centro_custo=centro,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("125.50"),
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=50,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=-20,
        tipo=LancamentoFinanceiro.Tipo.DESPESA,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    with django_assert_num_queries(6):
        data = gerar_relatorio(centro=str(centro.id))
    assert data["saldo_atual"] == pytest.approx(125.50)
    assert data["serie"][0]["receitas"] == 50.0
    assert data["serie"][0]["despesas"] == 20.0
    assert data["saldos_por_centro"][str(centro.id)] == pytest.approx(125.50)
    classificacoes = {item["id"]: item for item in data["classificacao_centros"]}
    assert classificacoes[str(centro.id)]["nome"] == centro.nome
    assert classificacoes[str(centro.id)]["tipo"] == centro.tipo


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_relatorios_usuario_nao_admin(client):
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro = CentroCusto.objects.create(nome="C", tipo="nucleo", organizacao=org, nucleo=nucleo)
    Carteira.objects.create(
        centro_custo=centro,
        nome="Operacional",
        tipo=Carteira.Tipo.OPERACIONAL,
        saldo=Decimal("89.30"),
    )
    user = UserFactory(user_type=UserType.COORDENADOR, nucleo_obj=nucleo)
    ParticipacaoNucleo.objects.create(user=user, nucleo=nucleo, status="ativo")
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=10,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    client.force_login(user)
    url = reverse("financeiro_api:financeiro-relatorios")
    resp = client.get(url)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["saldo_atual"] == pytest.approx(89.30)
    assert payload["saldos_por_centro"][str(centro.id)] == pytest.approx(89.30)


def test_relatorio_fallback_sem_carteira(django_assert_num_queries):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="Sem Carteira", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=75,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    with django_assert_num_queries(14, exact=False):
        data = gerar_relatorio(centro=str(centro.id))
    assert data["saldo_atual"] == pytest.approx(75.0)
    assert data["saldos_por_centro"][str(centro.id)] == pytest.approx(75.0)
    assert any(item["saldo"] == pytest.approx(75.0) for item in data["classificacao_centros"])


@override_settings(FINANCEIRO_SOMENTE_CARTEIRA=False)
def test_relatorio_legacy_emite_aviso():
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(
        nome="Legado",
        tipo="organizacao",
        organizacao=org,
        saldo=Decimal("42.00"),
    )
    with pytest.warns(DeprecationWarning):
        data = gerar_relatorio(centro=str(centro.id))
    assert data["saldo_atual"] == pytest.approx(42.0)
