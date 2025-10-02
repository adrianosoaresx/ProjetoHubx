import pytest

from nucleos.forms import NucleoForm, NucleoSearchForm

pytestmark = pytest.mark.django_db


def test_nucleo_form_fields():
    form = NucleoForm()
    assert list(form.fields) == [
        "nome",
        "descricao",
        "classificacao",
        "avatar",
        "cover",
        "mensalidade",
        "ativo",
    ]


def test_form_validation_errors():
    form = NucleoForm(data={"nome": ""})
    assert not form.is_valid()
    assert "nome" in form.errors


def test_mensalidade_negative_value():
    form = NucleoForm(data={"nome": "N", "mensalidade": -1})
    assert not form.is_valid()
    assert "mensalidade" in form.errors


def test_search_form_contains_field():
    form = NucleoSearchForm()
    assert "q" in form.fields
