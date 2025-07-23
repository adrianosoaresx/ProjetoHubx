import os

import pytest
from django.urls import reverse
from validate_docbr import CNPJ

from empresas.models import ContatoEmpresa, Empresa
from tests.empresas.utils import image_file

pytestmark = pytest.mark.django_db


def _empresa_post_data(user):
    return {
        "razao_social": "Empresa Z",
        "nome_fantasia": "Fantasia",
        "cnpj": CNPJ().generate(),
        "ramo_atividade": "TI",
        "endereco": "Rua B",
        "cidade": "Floripa",
        "estado": "SC",
        "cep": "88000-000",
        "email_corporativo": "contato@example.com",
        "telefone_corporativo": "123",
        "site": "http://ex.com",
        "rede_social": "",
        "organizacao": user.organizacao.pk,
    }


def test_listagem_empresas_autenticado(client, gerente_user, empresa):
    client.force_login(gerente_user)
    resp = client.get(reverse("empresas:lista"))
    assert resp.status_code == 200
    assert list(resp.context["empresas"]) == [empresa]


def test_listagem_empresas_anonymous(client):
    resp = client.get(reverse("empresas:lista"))
    assert resp.status_code == 302


def test_criacao_empresa_permitida(client, gerente_user):
    client.force_login(gerente_user)
    logo = image_file("logo.png")
    data = _empresa_post_data(gerente_user)
    url = reverse("empresas:nova")
    resp = client.post(url, data | {"logo": logo})
    assert resp.status_code in {201, 302}
    empresa = Empresa.objects.latest("id")
    assert empresa.usuario == gerente_user


def test_criacao_empresa_negada_admin(client, admin_user):
    client.force_login(admin_user)
    resp = client.post(reverse("empresas:nova"), _empresa_post_data(admin_user))
    assert resp.status_code == 403


def test_edicao_empresa(client, gerente_user, empresa):
    client.force_login(gerente_user)
    url = reverse("empresas:editar", args=[empresa.pk])
    data = _empresa_post_data(gerente_user)
    resp = client.post(url, data | {"cnpj": empresa.cnpj})
    assert resp.status_code in {200, 302}
    empresa.refresh_from_db()
    assert empresa.razao_social == data["razao_social"]


def test_edicao_empresa_proibida_para_outro_usuario(client, gerente_user, empresa, associado_user):
    client.force_login(associado_user)
    resp = client.post(reverse("empresas:editar", args=[empresa.pk]), _empresa_post_data(associado_user))
    assert resp.status_code == 403


def test_exclusao_empresa(client, gerente_user, empresa):
    client.force_login(gerente_user)
    logo = image_file("logo.png")
    empresa.logo.save("logo.png", logo)
    path = empresa.logo.path
    resp = client.post(reverse("empresas:remover", args=[empresa.pk]), HTTP_HX_REQUEST="true")
    assert resp.status_code == 204
    assert not Empresa.objects.filter(id=empresa.id).exists()
    assert os.path.exists(path)


def test_adicionar_contato(client, gerente_user, empresa):
    client.force_login(gerente_user)
    url = reverse("empresas:contato_novo", args=[empresa.id])
    resp = client.post(
        url,
        {
            "nome": "Novo",
            "cargo": "Dev",
            "email": "novo@example.com",
            "telefone": "123",
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 201
    assert ContatoEmpresa.objects.filter(empresa=empresa, email="novo@example.com").exists()


def test_editar_contato(client, gerente_user, contato_principal):
    client.force_login(gerente_user)
    url = reverse("empresas:contato_editar", args=[contato_principal.pk])
    resp = client.post(
        url,
        {
            "nome": contato_principal.nome,
            "cargo": contato_principal.cargo,
            "email": "edit@example.com",
            "telefone": "999",
        },
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    contato_principal.refresh_from_db()
    assert contato_principal.email == "edit@example.com"


def test_remover_contato(client, gerente_user, contato_principal):
    client.force_login(gerente_user)
    url = reverse("empresas:contato_remover", args=[contato_principal.pk])
    resp = client.post(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 204
    assert not ContatoEmpresa.objects.filter(id=contato_principal.id).exists()
