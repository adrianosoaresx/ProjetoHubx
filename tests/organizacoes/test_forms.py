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
        "avatar",
        "cover",
    ]


def test_cnpj_duplicate_invalid(faker_ptbr):
    cnpj = faker_ptbr.cnpj()
    Organizacao.objects.create(nome="Org", cnpj=cnpj, slug="org")
    form = OrganizacaoForm(data={"nome": "Outra", "cnpj": cnpj, "slug": "org2"})
    assert not form.is_valid()
    assert "cnpj" in form.errors


def test_slug_required(faker_ptbr):
    data = {"nome": "Sem Slug", "cnpj": faker_ptbr.cnpj()}
    form = OrganizacaoForm(data=data)
    assert not form.is_valid()
    assert "slug" in form.errors
