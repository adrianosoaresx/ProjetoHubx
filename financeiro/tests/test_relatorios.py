import csv
import io

import pytest
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, LancamentoFinanceiro
from financeiro.services.relatorios import gerar_relatorio
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


def test_gera_serie_temporal(django_assert_num_queries):
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
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
    with django_assert_num_queries(4):
        data = gerar_relatorio(centro=str(centro.id))
    assert data["saldo_atual"] == float(centro.saldo)
    assert data["serie"][0]["receitas"] == 50.0
    assert data["serie"][0]["despesas"] == 20.0


def test_exporta_csv_relatorios(client):
    user = UserFactory(user_type=UserType.ADMIN)
    client.force_login(user)
    org = OrganizacaoFactory()
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        valor=50,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        data_lancamento=timezone.now(),
        status=LancamentoFinanceiro.Status.PAGO,
    )
    url = reverse("financeiro_api:financeiro-relatorios") + "?format=csv"
    resp = client.get(url)
    assert resp.status_code == 200
    reader = csv.reader(io.StringIO(resp.content.decode()))
    rows = list(reader)
    assert rows[0] == ["data", "categoria", "valor", "status", "centro de custo"]
    assert len(rows) == 2


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_relatorios_usuario_nao_admin(client):
    org = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=org)
    centro = CentroCusto.objects.create(
        nome="C", tipo="nucleo", organizacao=org, nucleo=nucleo
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
    assert resp.json()["saldo_atual"] == float(centro.saldo)
