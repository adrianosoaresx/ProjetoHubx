import pytest
from django.db import IntegrityError
from validate_docbr import CNPJ

from empresas.forms import ContatoEmpresaForm, EmpresaForm
from tests.empresas.utils import image_file

pytestmark = pytest.mark.django_db


def test_empresaform_fields():
    form = EmpresaForm()
    expected = {
        "organizacao",
        "razao_social",
        "nome_fantasia",
        "cnpj",
        "ramo_atividade",
        "endereco",
        "cidade",
        "estado",
        "cep",
        "email_corporativo",
        "telefone_corporativo",
        "site",
        "rede_social",
        "logo",
        "banner",
        "tags_field",
    }
    assert set(form.fields.keys()) == expected


def test_empresaform_cnpj_validation(gerente_user):
    data = {
        "razao_social": "Empresa X",
        "nome_fantasia": "Fantasia",
        "cnpj": "12.345.678/0001-90",
        "ramo_atividade": "TI",
        "endereco": "Rua 1",
        "cidade": "X",
        "estado": "SC",
        "cep": "88000-000",
        "email_corporativo": "e@e.com",
        "telefone_corporativo": "123",
    }
    form = EmpresaForm(data=data | {"organizacao": gerente_user.organizacao.pk})
    assert not form.is_valid()
    assert "cnpj" in form.errors


def test_empresaform_optional_banner(gerente_user):
    data = {
        "razao_social": "Empresa Y",
        "nome_fantasia": "Fantasia",
        "cnpj": CNPJ().generate(),
        "ramo_atividade": "TI",
        "endereco": "Rua A",
        "cidade": "S",
        "estado": "SC",
        "cep": "88000-000",
        "email_corporativo": "e@e.com",
        "telefone_corporativo": "123",
    }
    logo = image_file("logo.png")
    form = EmpresaForm(
        data=data | {"organizacao": gerente_user.organizacao.pk},
        files={"logo": logo},
        initial={"usuario": gerente_user, "organizacao": gerente_user.organizacao},
    )
    assert form.is_valid()


def test_contatoempresaform_unique_email(contato_principal, empresa):
    form = ContatoEmpresaForm(
        data={
            "nome": "Outro",
            "cargo": "Dev",
            "email": contato_principal.email,
            "telefone": "123",
        }
    )
    form.instance.empresa = empresa
    assert form.is_valid(), form.errors
    with pytest.raises(IntegrityError):
        form.save()


def test_contatoempresaform_toggle_principal(contato_principal, empresa):
    form = ContatoEmpresaForm(
        data={
            "nome": "Novo",
            "cargo": "Gerente",
            "email": "novo@example.com",
            "telefone": "321",
            "principal": True,
        }
    )
    form.instance.empresa = empresa
    assert form.is_valid(), form.errors
    novo = form.save()
    contato_principal.refresh_from_db()
    assert novo.principal
    assert not contato_principal.principal


def test_contatoempresaform_phone_formats(empresa):
    form = ContatoEmpresaForm(
        data={
            "nome": "Tel",
            "cargo": "TI",
            "email": "tel@example.com",
            "telefone": "(48) 9999-0000",
        }
    )
    form.instance.empresa = empresa
    assert form.is_valid()
    contato = form.save()
    assert contato.telefone
