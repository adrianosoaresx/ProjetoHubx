import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from nucleos.forms import NucleoForm, NucleoSearchForm, SuplenteForm
from nucleos.models import Nucleo, ParticipacaoNucleo
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


def test_nucleo_form_fields():
    form = NucleoForm()
    assert list(form.fields) == [
        "nome",
        "descricao",
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


def test_suplente_form_date_validation():
    form = SuplenteForm(data={"usuario": None, "periodo_inicio": "2024-01-02", "periodo_fim": "2024-01-01"})
    assert not form.is_valid()


def test_suplente_form_usuario_queryset_filters_active_members():
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")
    nucleo = Nucleo.objects.create(nome="N", organizacao=org)
    User = get_user_model()
    ativo = User.objects.create_user(
        username="a",
        email="a@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=org,
    )
    inativo = User.objects.create_user(
        username="i",
        email="i@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=org,
    )
    ParticipacaoNucleo.objects.create(nucleo=nucleo, user=ativo, status="ativo")
    ParticipacaoNucleo.objects.create(nucleo=nucleo, user=inativo, status="inativo")
    form = SuplenteForm(nucleo=nucleo)
    assert list(form.fields["usuario"].queryset) == [ativo]
