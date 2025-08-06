import pytest
from django.http import QueryDict

from empresas.factories import EmpresaFactory
from empresas.services import search_empresas


@pytest.mark.django_db
def test_search_considers_tags(admin_user, tag_factory):
    tag = tag_factory(nome="Tech")
    empresa = EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Alpha")
    empresa.tags.add(tag)
    EmpresaFactory(usuario=admin_user, organizacao=admin_user.organizacao, nome="Beta")
    qs = search_empresas(admin_user, QueryDict("q=Tech"))
    assert list(qs) == [empresa]
