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
        "tipo",
        "rua",
        "cidade",
        "estado",
        "contato_nome",
        "contato_email",
        "contato_telefone",
        "chave_pix",
        "nome_site",
        "site",
        "icone_site",
        "feed_noticias",
        "avatar",
        "cover",
    ]


def test_cnpj_duplicate_invalid(faker_ptbr):
    cnpj = faker_ptbr.cnpj()
    Organizacao.objects.create(nome="Org", cnpj=cnpj)
    form = OrganizacaoForm(data={"nome": "Outra", "cnpj": cnpj})
    assert not form.is_valid()
    assert "cnpj" in form.errors


def test_cnpj_invalid_value():
    form = OrganizacaoForm(data={"nome": "Org", "cnpj": "12345678901234"})
    assert not form.is_valid()
    assert "cnpj" in form.errors
