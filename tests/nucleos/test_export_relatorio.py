import csv
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserType
from agenda.factories import EventoFactory
from nucleos.models import Nucleo, ParticipacaoNucleo

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def organizacao():
    from organizacoes.models import Organizacao

    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00")


@pytest.fixture
def admin_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def outro_user(organizacao, django_user_model):
    return django_user_model.objects.create_user(
        username="outro",
        email="outro@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


def _auth(client, user):
    client.force_authenticate(user=user)


def test_exportar_relatorio(api_client, admin_user, outro_user, organizacao):
    nucleo = Nucleo.objects.create(nome="R1", slug="r1", organizacao=organizacao)
    ParticipacaoNucleo.objects.create(user=outro_user, nucleo=nucleo, status="aprovado")
    EventoFactory(nucleo=nucleo, organizacao=organizacao, coordenador=admin_user)
    _auth(api_client, admin_user)
    url = reverse("nucleos_api:nucleo-relatorio")
    resp = api_client.get(url + "?formato=csv")
    assert resp.status_code == 200
    rows = list(csv.reader(resp.content.decode().splitlines()))
    assert rows[0] == ["Núcleo", "Membros", "Eventos", "Datas"]
    assert rows[1][0] == nucleo.nome

    resp_pdf = api_client.get(url + "?formato=pdf")
    assert resp_pdf.status_code == 200
    assert resp_pdf["Content-Type"] == "application/pdf"

