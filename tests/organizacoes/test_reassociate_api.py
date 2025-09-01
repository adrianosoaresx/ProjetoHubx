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


def test_reassociate_existing_resources_returns_conflict(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    admin = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    api_client.force_authenticate(admin)

    user = UserFactory(organizacao=other_org, nucleo_obj=None)
    nucleo = NucleoFactory(organizacao=other_org)
    evento = EventoFactory(organizacao=other_org)
    empresa = EmpresaFactory(organizacao=other_org, usuario=UserFactory(organizacao=other_org, nucleo_obj=None))
    post = PostFactory(autor=UserFactory(organizacao=other_org, nucleo_obj=None), organizacao=other_org)

    endpoints = [
        ("organizacao-usuarios-list", {"user_id": user.pk}),
        ("organizacao-nucleos-list", {"nucleo_id": nucleo.pk}),
        ("organizacao-eventos-list", {"evento_id": evento.pk}),
        ("organizacao-empresas-list", {"empresa_id": empresa.pk}),
        ("organizacao-posts-list", {"post_id": post.pk}),
    ]

    for name, payload in endpoints:
        url = reverse(f"organizacoes_api:{name}", kwargs={"organizacao_pk": org.pk})
        resp = api_client.post(url, payload)
        assert resp.status_code == status.HTTP_409_CONFLICT
