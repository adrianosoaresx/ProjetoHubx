import pytest

from nucleos.forms import NucleoForm, NucleoSearchForm, SuplenteForm

pytestmark = pytest.mark.django_db


def test_nucleo_form_fields():
    form = NucleoForm()
    assert list(form.fields) == ["nome", "slug", "descricao", "avatar", "cover", "ativo"]


def test_form_validation_errors():
    form = NucleoForm(data={"nome": "", "slug": ""})
    assert not form.is_valid()
    assert "nome" in form.errors


def test_search_form_contains_field():
    form = NucleoSearchForm()
    assert "q" in form.fields


def test_suplente_form_date_validation():
    form = SuplenteForm(
        data={"usuario": None, "periodo_inicio": "2024-01-02", "periodo_fim": "2024-01-01"}
    )
    assert not form.is_valid()
