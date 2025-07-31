import pytest

from nucleos.forms import NucleoForm, NucleoSearchForm, SuplenteForm
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")


def test_nucleo_form_fields():
    form = NucleoForm()
    assert list(form.fields) == [
        "organizacao",
        "nome",
        "descricao",
        "avatar",
        "cover",
    ]


def test_membros_queryset_includes_all_users():
    form = NucleoForm()
    assert "organizacao" in form.fields


def test_form_validation_errors(organizacao):
    form = NucleoForm(data={"organizacao": organizacao.pk, "nome": ""})
    assert not form.is_valid()
    assert "nome" in form.errors


def test_search_form_contains_field():
    form = NucleoSearchForm()
    assert "q" in form.fields


def test_suplente_form_date_validation():
    form = SuplenteForm(data={"usuario": None, "periodo_inicio": "2024-01-02", "periodo_fim": "2024-01-01"})
    assert not form.is_valid()
