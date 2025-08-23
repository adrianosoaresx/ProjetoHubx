import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from organizacoes.factories import OrganizacaoFactory
from nucleos.factories import NucleoFactory
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from feed.factories import PostFactory
from accounts.factories import UserFactory
from nucleos.models import Nucleo
from agenda.models import Evento
from empresas.models import Empresa
from feed.models import Post


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root_user():
    return User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="pass",
    )


def auth(client, user):
    client.force_authenticate(user=user)


@pytest.mark.parametrize(
    "model,make_obj,endpoint",
    [
        (Nucleo, lambda org: NucleoFactory(organizacao=org), "organizacao-nucleos"),
        (Evento, lambda org: EventoFactory(organizacao=org), "organizacao-eventos"),
        (Empresa, lambda org: EmpresaFactory(organizacao=org), "organizacao-empresas"),
        (
            Post,
            lambda org: PostFactory(
                autor=UserFactory(organizacao=org, nucleo_obj=NucleoFactory(organizacao=org)),
                organizacao=org,
            ),
            "organizacao-posts",
        ),
    ],
)

def test_associacao_generica(api_client, root_user, model, make_obj, endpoint):
    auth(api_client, root_user)
    org = OrganizacaoFactory()
    other_org = OrganizacaoFactory()
    obj = make_obj(other_org)

    list_url = reverse(f"organizacoes_api:{endpoint}-list", kwargs={"organizacao_pk": org.pk})
    resp = api_client.get(list_url)
    assert resp.status_code == status.HTTP_200_OK
    assert str(obj.id) in {str(o["id"]) for o in resp.data}

    data = {f"{model.__name__.lower()}_id": str(obj.pk)}
    resp = api_client.post(list_url, data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    obj.refresh_from_db()
    assert obj.organizacao_id == org.pk

    detail_url = reverse(
        f"organizacoes_api:{endpoint}-detail",
        kwargs={"organizacao_pk": org.pk, "pk": obj.pk},
    )
    resp = api_client.delete(detail_url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not model.objects.filter(pk=obj.pk, deleted=False).exists()
