import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import CentroCusto, ContaAssociado, LancamentoFinanceiro
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_importar_pagamentos_restrito(api_client):
    user = UserFactory(user_type=UserType.ASSOCIADO)
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    file = SimpleUploadedFile("data.csv", b"x", content_type="text/csv")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code == 403


@pytest.mark.parametrize("tipo", [UserType.ADMIN, UserType.FINANCEIRO])
def test_importar_pagamentos_permitido(api_client, tipo):
    user = UserFactory(user_type=tipo)
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:financeiro-importar-pagamentos")
    file = SimpleUploadedFile("data.csv", b"x", content_type="text/csv")
    resp = api_client.post(url, {"file": file}, format="multipart")
    assert resp.status_code != 403


def test_financeiro_pode_criar_centro(api_client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.FINANCEIRO, organizacao=org)
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:centro-list")
    payload = {"nome": "C", "tipo": "organizacao", "organizacao": str(org.id)}
    resp = api_client.post(url, payload)
    assert resp.status_code == 201


def test_associado_somente_seus_lancamentos(api_client):
    org = OrganizacaoFactory()
    user1 = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org)
    user2 = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org)
    conta1 = ContaAssociado.objects.create(user=user1)
    conta2 = ContaAssociado.objects.create(user=user2)
    centro = CentroCusto.objects.create(nome="C", tipo="organizacao", organizacao=org)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta1,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=50,
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        conta_associado=conta2,
        tipo=LancamentoFinanceiro.Tipo.MENSALIDADE_ASSOCIACAO,
        valor=60,
        status=LancamentoFinanceiro.Status.PENDENTE,
    )
    api_client.force_authenticate(user=user1)
    url = reverse("financeiro_api:financeiro-inadimplencias")
    resp = api_client.get(url)
    assert resp.status_code == 200
    assert len(resp.data) == 1


def test_coordenador_limita_centro(api_client):
    org = OrganizacaoFactory()
    coord = UserFactory(user_type=UserType.COORDENADOR, organizacao=org)
    outro = UserFactory(user_type=UserType.COORDENADOR, organizacao=org)
    centro1 = CentroCusto.objects.create(nome="C1", tipo="nucleo", nucleo=coord.nucleo)
    centro2 = CentroCusto.objects.create(nome="C2", tipo="nucleo", nucleo=outro.nucleo)
    api_client.force_authenticate(user=coord)
    url = reverse("financeiro_api:centro-list")
    resp = api_client.get(url)
    ids = {item["id"] for item in resp.data}
    assert str(centro1.id) in ids and str(centro2.id) not in ids

def test_root_sem_acesso_listagem(api_client):
    user = UserFactory(user_type=UserType.ROOT)
    api_client.force_authenticate(user=user)
    url = reverse("financeiro_api:centro-list")
    resp = api_client.get(url)
    assert resp.status_code == 403
