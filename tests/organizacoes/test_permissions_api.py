import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from feed.factories import PostFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_related_viewsets_permissions(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    admin = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    other_admin = UserFactory(user_type=UserType.ADMIN, organizacao=other_org, nucleo_obj=None)
    root = UserFactory(user_type=UserType.ROOT, organizacao=None, nucleo_obj=None)

    associado = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org, nucleo_obj=None)
    nucleo = NucleoFactory(organizacao=org)
    EventoFactory(organizacao=org, coordenador=admin, nucleo=nucleo)
    EmpresaFactory(organizacao=org, usuario=admin)
    PostFactory(autor=admin, organizacao=org)

    endpoints = [
        "organizacao-usuarios-list",
        "organizacao-usuarios-associados",
        "organizacao-nucleos-list",
        "organizacao-eventos-list",
        "organizacao-empresas-list",
        "organizacao-posts-list",
    ]

    for name in endpoints:
        url = reverse(f"organizacoes_api:{name}", kwargs={"organizacao_pk": org.pk})
        api_client.force_authenticate(admin)
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        api_client.force_authenticate(root)
        assert api_client.get(url).status_code == status.HTTP_200_OK
        api_client.force_authenticate(other_admin)
        assert api_client.get(url).status_code == status.HTTP_403_FORBIDDEN
