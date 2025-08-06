import pytest
from validate_docbr import CNPJ

from empresas.models import Empresa, ContatoEmpresa


@pytest.mark.django_db
def test_get_contato_principal(nucleado_user):
    empresa = Empresa.objects.create(
        usuario=nucleado_user,
        organizacao=nucleado_user.organizacao,
        nome="E",
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )
    assert empresa.get_contato_principal() is None
    c1 = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="A",
        cargo="C",
        email="a@a.com",
        telefone="1",
        principal=False,
    )
    assert empresa.get_contato_principal() == c1
    c2 = ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="B",
        cargo="C",
        email="b@a.com",
        telefone="2",
        principal=True,
    )
    assert empresa.get_contato_principal() == c2
