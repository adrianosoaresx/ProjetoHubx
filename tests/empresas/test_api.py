import os

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from validate_docbr import CNPJ

from empresas.models import AvaliacaoEmpresa, Empresa, EmpresaChangeLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def celery_eager(settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    monkeypatch.setattr("empresas.tasks.notificar_responsavel.delay", lambda *a, **k: None)


def test_crud_empresa(api_client, gerente_user, tag_factory):
    api_client.force_authenticate(user=gerente_user)
    url = reverse("empresas_api:empresa-list")
    tag = tag_factory(nome="Teste", categoria="prod")
    data = {
        "usuario": gerente_user.id,
        "organizacao": gerente_user.organizacao.id,
        "nome": "Empresa X",
        "cnpj": CNPJ().generate(),
        "tipo": "mei",
        "municipio": "Florianópolis",
        "estado": "SC",
        "palavras_chave": "tech",
        "tags": [tag.id],
    }
    resp = api_client.post(url, data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    empresa_id = resp.data["id"]
    assert list(Empresa.objects.get(pk=empresa_id).tags.values_list("id", flat=True)) == [tag.id]

    # duplicate cnpj
    resp_dup = api_client.post(url, {**data, "cnpj": data["cnpj"]})
    assert resp_dup.status_code == status.HTTP_400_BAD_REQUEST

    # update
    detail_url = reverse("empresas_api:empresa-detail", args=[empresa_id])
    resp = api_client.patch(detail_url, {"nome": "Nova"})
    assert resp.status_code == status.HTTP_200_OK
    assert EmpresaChangeLog.objects.filter(empresa_id=empresa_id, campo_alterado="nome").exists()

    # delete
    resp = api_client.delete(detail_url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    empresa = Empresa.objects.get(pk=empresa_id)
    assert empresa.deleted is True
    EmpresaChangeLog.objects.get(empresa=empresa, campo_alterado="deleted", valor_novo="True")


def test_busca_por_tag_e_palavra(api_client, gerente_user, tag_factory):
    api_client.force_authenticate(user=gerente_user)
    t1 = tag_factory(nome="servico", categoria="serv")
    t2 = tag_factory(nome="outro", categoria="prod")
    e1 = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Alpha",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
        palavras_chave="saude",
    )
    e1.tags.add(t1)
    e2 = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Beta",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="Y",
        estado="SC",
        palavras_chave="tech",
    )
    e2.tags.add(t2)

    url = reverse("empresas_api:empresa-list") + f"?tag={t1.id}&q=saude"
    resp = api_client.get(url)
    ids = [e["id"] for e in resp.data]
    assert str(e1.id) in ids and str(e2.id) not in ids


def test_busca_palavras_chave(api_client, gerente_user):
    api_client.force_authenticate(user=gerente_user)
    e1 = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Alpha",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
        palavras_chave="saude",
    )
    Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Beta",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="Y",
        estado="SC",
        palavras_chave="tech",
    )
    url = reverse("empresas_api:empresa-list") + "?palavras_chave=saude"
    resp = api_client.get(url)
    ids = [e["id"] for e in resp.data]
    assert str(e1.id) in ids and len(resp.data) == 1


def test_avaliacao_unica(api_client, gerente_user):
    api_client.force_authenticate(user=gerente_user)
    empresa = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Avaliada",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )
    url = reverse("empresas_api:empresa-avaliacoes", args=[empresa.id])
    resp = api_client.post(url, {"nota": 5, "comentario": "ok"})
    assert resp.status_code == status.HTTP_201_CREATED
    assert AvaliacaoEmpresa.objects.filter(empresa=empresa, usuario=gerente_user).exists()
    resp = api_client.post(url, {"nota": 4})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_listar_avaliacoes(api_client, gerente_user, admin_user):
    api_client.force_authenticate(user=gerente_user)
    empresa = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Avaliada",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )
    AvaliacaoEmpresa.objects.create(empresa=empresa, usuario=gerente_user, nota=5)
    AvaliacaoEmpresa.objects.create(empresa=empresa, usuario=admin_user, nota=3, deleted=True)
    url = reverse("empresas_api:empresa-avaliacoes", args=[empresa.id])
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 1


def test_historico_restrito(api_client, gerente_user, admin_user):
    empresa = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Hist",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )
    EmpresaChangeLog.objects.create(
        empresa=empresa,
        usuario=gerente_user,
        campo_alterado="nome",
        valor_antigo="Hist",
        valor_novo="Novo",
    )
    url = reverse("empresas_api:empresa-historico", args=[empresa.id])
    api_client.force_authenticate(user=gerente_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    api_client.force_authenticate(user=admin_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 1


def test_permissoes_edicao(api_client, gerente_user, nucleado_user, admin_user):
    empresa = Empresa.objects.create(
        usuario=gerente_user,
        organizacao=gerente_user.organizacao,
        nome="Privada",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )
    url = reverse("empresas_api:empresa-detail", args=[empresa.id])
    api_client.force_authenticate(user=nucleado_user)
    resp = api_client.patch(url, {"nome": "X"})
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    api_client.force_authenticate(user=admin_user)
    resp = api_client.patch(url, {"nome": "Y"})
    assert resp.status_code == status.HTTP_200_OK
    api_client.force_authenticate(user=gerente_user)
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
