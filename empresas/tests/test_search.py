import pytest
from django.http import QueryDict

from accounts.factories import UserFactory
from accounts.models import UserType
from empresas.factories import EmpresaFactory
from empresas.services import search_empresas


@pytest.mark.django_db
def test_search_empresas_by_cnpj():
    empresa = EmpresaFactory(cnpj="12.345.678/0001-90")
    user = UserFactory(is_superuser=True, user_type=UserType.ROOT)
    params = QueryDict(mutable=True)
    params["q"] = empresa.cnpj
    qs = search_empresas(user, params)
    assert list(qs) == [empresa]
