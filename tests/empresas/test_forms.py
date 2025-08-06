import pytest
from validate_docbr import CNPJ

from empresas.forms import EmpresaForm


@pytest.mark.django_db
def test_clean_cnpj_formats_and_unique(nucleado_user):
    cnpj_num = CNPJ().generate()
    form = EmpresaForm(
        data={
            "nome": "X",
            "cnpj": cnpj_num,
            "tipo": "mei",
            "municipio": "A",
            "estado": "SC",
            "descricao": "",
            "palavras_chave": "",
            "tags_field": "",
        },
        initial={"usuario": nucleado_user, "organizacao": nucleado_user.organizacao},
    )
    assert form.is_valid()
    mask = f"{cnpj_num[:2]}.{cnpj_num[2:5]}.{cnpj_num[5:8]}/{cnpj_num[8:12]}-{cnpj_num[12:14]}"
    assert form.cleaned_data["cnpj"] == mask
    form.instance.usuario = nucleado_user
    form.instance.organizacao = nucleado_user.organizacao
    form.save()
    form2 = EmpresaForm(
        data={
            "nome": "Y",
            "cnpj": cnpj_num,
            "tipo": "mei",
            "municipio": "B",
            "estado": "SC",
            "descricao": "",
            "palavras_chave": "",
            "tags_field": "",
        },
        initial={"usuario": nucleado_user, "organizacao": nucleado_user.organizacao},
    )
    assert not form2.is_valid()
    assert "cnpj" in form2.errors


@pytest.mark.django_db
def test_clean_cnpj_invalid(nucleado_user):
    form = EmpresaForm(
        data={
            "nome": "X",
            "cnpj": "123",
            "tipo": "mei",
            "municipio": "A",
            "estado": "SC",
            "descricao": "",
            "palavras_chave": "",
            "tags_field": "",
        },
        initial={"usuario": nucleado_user, "organizacao": nucleado_user.organizacao},
    )
    assert not form.is_valid()
    assert "cnpj" in form.errors
