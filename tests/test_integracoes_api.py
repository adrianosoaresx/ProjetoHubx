import pytest
from django.urls import include, path, reverse
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from financeiro.models import IntegracaoConfig

urlpatterns = [
    path("api/financeiro/", include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api")),
]


@pytest.fixture
def api_client():
    return APIClient()


@override_settings(ROOT_URLCONF=__name__)
@pytest.mark.django_db
def test_delete_integracao(api_client):
    user = UserFactory(user_type=UserType.ADMIN)
    api_client.force_authenticate(user=user)
    org = OrganizacaoFactory()
    integracao = IntegracaoConfig.objects.create(
        organizacao=org,
        nome="Test",
        tipo="erp",
        base_url="http://example.com",
    )
    url = reverse("financeiro_api:integracao-detail", args=[integracao.id])
    response = api_client.delete(url)
    assert response.status_code == 204
    assert not IntegracaoConfig.objects.filter(id=integracao.id).exists()
