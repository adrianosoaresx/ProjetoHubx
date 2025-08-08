import pytest

import pytest

from organizacoes.forms import OrganizacaoForm
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


def test_form_fields():
    form = OrganizacaoForm()
    assert list(form.fields.keys()) == [
        "nome",
        "cnpj",
        "descricao",
        "slug",
        "tipo",
        "rua",
        "cidade",
        "estado",
        "contato_nome",
        "contato_email",
        "contato_telefone",
        "avatar",
        "cover",
    ]


def test_cnpj_duplicate_invalid(faker_ptbr):
    cnpj = faker_ptbr.cnpj()
    Organizacao.objects.create(nome="Org", cnpj=cnpj, slug="org")
    form = OrganizacaoForm(data={"nome": "Outra", "cnpj": cnpj})
    assert not form.is_valid()
    assert "cnpj" in form.errors


def test_cnpj_invalid_value():
    form = OrganizacaoForm(data={"nome": "Org", "cnpj": "12345678901234"})
    assert not form.is_valid()
    assert "cnpj" in form.errors


def test_slug_auto_generation_and_uniqueness(faker_ptbr):
    name = "Nova Org"
    form = OrganizacaoForm(data={"nome": name, "cnpj": faker_ptbr.cnpj()})
    assert form.is_valid()
    org = form.save()
    assert org.slug == "nova-org"
    form2 = OrganizacaoForm(data={"nome": name, "cnpj": faker_ptbr.cnpj()})
    assert form2.is_valid()
    org2 = form2.save()
    assert org2.slug == "nova-org-2"


def test_slug_unique_and_slugified(faker_ptbr):
    cnpj1 = faker_ptbr.cnpj()
    Organizacao.objects.create(nome="Org1", cnpj=cnpj1, slug="org1")
    data = {"nome": "Org2", "cnpj": faker_ptbr.cnpj(), "slug": "Org1"}
    form = OrganizacaoForm(data=data)
    assert form.is_valid()
    assert form.cleaned_data["slug"] == "org1-2"
    form2 = OrganizacaoForm(data={"nome": "Org3", "cnpj": faker_ptbr.cnpj(), "slug": "NOVA-ORG"})
    assert form2.is_valid()
    assert form2.cleaned_data["slug"] == "nova-org"
