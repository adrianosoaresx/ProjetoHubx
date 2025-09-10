import pytest
from django.urls import include, path, reverse
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from empresas.factories import EmpresaFactory
from empresas.models import EmpresaChangeLog
from organizacoes.factories import OrganizacaoFactory


urlpatterns = [
    path("api/", include(("empresas.api_urls", "empresas_api"), namespace="empresas_api")),
]


@pytest.fixture
def api_client():
    return APIClient()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_delete_empresa_soft_delete(api_client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    empresa = EmpresaFactory(usuario=user, organizacao=org)
    api_client.force_authenticate(user=user)
    url = reverse("empresas_api:empresa-detail", args=[empresa.id])
    response = api_client.delete(url)
    assert response.status_code == 204
    empresa.refresh_from_db()
    assert empresa.deleted is True
    assert empresa.deleted_at is not None
    log = EmpresaChangeLog.objects.filter(empresa=empresa, campo_alterado="deleted").first()
    assert log is not None
    assert log.valor_antigo == "False"
    assert log.valor_novo == "True"
