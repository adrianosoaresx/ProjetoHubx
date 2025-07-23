import os

import pytest
from django.db import IntegrityError
from validate_docbr import CNPJ

from empresas.forms import EmpresaForm
from empresas.models import ContatoEmpresa, Empresa
from tests.empresas.utils import image_file

pytestmark = pytest.mark.django_db


def test_empresa_str(empresa):
    assert str(empresa) == empresa.razao_social


def test_unique_cnpj(empresa, gerente_user):
    with pytest.raises(IntegrityError):
        Empresa.objects.create(
            usuario=gerente_user,
            organizacao=gerente_user.organizacao,
            razao_social="Outra",
            nome_fantasia="Outra",
            cnpj=empresa.cnpj,
            ramo_atividade="TI",
            endereco="Rua 1",
            cidade="X",
            estado="SC",
            cep="00000-000",
            email_corporativo="a@a.com",
            telefone_corporativo="123",
        )


def test_form_required_fields(gerente_user):
    form = EmpresaForm(data={"organizacao": gerente_user.organizacao.pk})
    assert not form.is_valid()
    assert "razao_social" in form.errors
    assert "cnpj" in form.errors


def test_logo_banner_upload_and_delete(gerente_user, settings, tmp_path):
    data = {
        "razao_social": "Empresa Logo",
        "nome_fantasia": "Fantasia",
        "cnpj": CNPJ().generate(),
        "ramo_atividade": "TI",
        "endereco": "Rua A",
        "cidade": "S",
        "estado": "SC",
        "cep": "88000-000",
        "email_corporativo": "e@e.com",
        "telefone_corporativo": "123",
        "site": "http://example.com",
        "rede_social": "",
        "organizacao": gerente_user.organizacao.pk,
    }
    logo = image_file("logo.png")
    banner = image_file("banner.png")
    form = EmpresaForm(
        data=data,
        files={"logo": logo, "banner": banner},
        initial={"usuario": gerente_user, "organizacao": gerente_user.organizacao},
    )
    assert form.is_valid(), form.errors
    empresa = form.save()
    logo_path = empresa.logo.path
    banner_path = empresa.banner.path
    assert os.path.exists(logo_path)
    assert os.path.exists(banner_path)
    empresa.delete()
    assert os.path.exists(logo_path)
    assert os.path.exists(banner_path)


def test_unique_email_contato(contato_principal, empresa):
    with pytest.raises(IntegrityError):
        ContatoEmpresa.objects.create(
            empresa=empresa,
            nome="Outro",
            cargo="Dev",
            email=contato_principal.email,
            telefone="3333",
        )


def test_only_one_principal(contato_principal, empresa):
    novo = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Novo",
        cargo="Gerente",
        email="novo@example.com",
        telefone="4444",
        principal=True,
    )
    contato_principal.refresh_from_db()
    assert not contato_principal.principal
    assert novo.principal


def test_contato_associado_a_empresa(empresa):
    contato = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Fulano",
        cargo="CEO",
        email="fulano@example.com",
        telefone="5555",
    )
    assert contato.empresa == empresa
