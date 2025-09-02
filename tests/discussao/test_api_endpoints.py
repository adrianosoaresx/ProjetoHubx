import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from discussao.factories import CategoriaDiscussaoFactory, TopicoDiscussaoFactory
from agenda.factories import EventoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_categoria_viewset_filters(api_client):
    user = UserFactory()
    org = user.nucleo.organizacao
    nucleo = user.nucleo
    evento = EventoFactory(organizacao=org, nucleo=nucleo)

    cat_org = CategoriaDiscussaoFactory(organizacao=org)
    cat_nucleo = CategoriaDiscussaoFactory(organizacao=org, nucleo=nucleo)
    cat_evento = CategoriaDiscussaoFactory(organizacao=org, evento=evento)
    CategoriaDiscussaoFactory()  # other org

    api_client.force_authenticate(user=user)

    resp = api_client.get(
        "/api/discussao/discussao/categorias/", {"organizacao": org.id}
    )
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()}
    assert ids == {cat_org.id, cat_nucleo.id, cat_evento.id}

    resp = api_client.get(
        "/api/discussao/discussao/categorias/", {"nucleo": nucleo.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1 and data[0]["id"] == cat_nucleo.id

    resp = api_client.get(
        "/api/discussao/discussao/categorias/", {"evento": evento.id}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1 and data[0]["id"] == cat_evento.id


def test_voto_endpoints(api_client, settings):
    settings.CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    user = UserFactory()
    topico = TopicoDiscussaoFactory()
    ct = ContentType.objects.get_for_model(topico)

    api_client.force_authenticate(user=user)

    url = "/api/discussao/discussao/votos/"
    resp = api_client.post(
        url,
        {"content_type_id": ct.id, "object_id": topico.id, "valor": 1},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 1

    resp = api_client.post(
        url,
        {"content_type_id": ct.id, "object_id": topico.id, "valor": 1},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 0
