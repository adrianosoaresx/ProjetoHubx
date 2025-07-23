import pytest
from django import forms

from nucleos.forms import NucleoForm, NucleoSearchForm
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
        "membros",
    ]
    assert isinstance(form.fields["membros"], forms.ModelMultipleChoiceField)


def test_membros_queryset_includes_all_users():
    form = NucleoForm()
    assert hasattr(form.fields["membros"], "queryset")


def test_form_validation_errors(organizacao):
    form = NucleoForm(data={"organizacao": organizacao.pk, "nome": ""})
    assert not form.is_valid()
    assert "nome" in form.errors


def test_search_form_contains_field():
    form = NucleoSearchForm()
    assert "nucleo" in form.fields
