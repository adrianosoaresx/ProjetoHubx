import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True


def test_evento_list_filtra_organizacao(api_client):
    org1 = OrganizacaoFactory()
    org2 = OrganizacaoFactory()
    user1 = UserFactory(organizacao=org1, nucleo_obj=None)
    user2 = UserFactory(organizacao=org2, nucleo_obj=None)
    EventoFactory(organizacao=org1, coordenador=user1)
    EventoFactory(organizacao=org2, coordenador=user2)
    api_client.force_authenticate(user1)
    url = reverse("agenda_api:evento-list")
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    ids = [e["id"] for e in resp.data["results"]]
    assert len(ids) == 1


def test_parceria_cnpj_invalido(api_client):
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, nucleo_obj=None)
    evento = EventoFactory(organizacao=org, coordenador=user)
    empresa = EmpresaFactory(organizacao=org, usuario=user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:parceria-list")
    data = {
        "evento": evento.id,
        "empresa": empresa.id,
        "cnpj": "123",
        "contato": "Fulano",
        "representante_legal": "Beltrano",
        "data_inicio": date.today(),
        "data_fim": date.today(),
        "tipo_parceria": "patrocinio",
    }
    resp = api_client.post(url, data)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
