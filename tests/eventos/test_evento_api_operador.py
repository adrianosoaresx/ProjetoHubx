import pytest
from datetime import datetime, timedelta

from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework.test import APIClient

from accounts.models import User, UserType
from eventos.models import Evento
from nucleos.models import Nucleo
from organizacoes.models import Organizacao


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(
        nome="Org API",
        cnpj="00000000000191",
        descricao="Organização API",
    )


@pytest.fixture
def usuario_operador(organizacao):
    return User.objects.create_user(
        username="operador_api",
        email="operador_api@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.OPERADOR,
    )


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(organizacao=organizacao, nome="Núcleo API")


def test_operador_lista_e_atualiza_evento(api_client, organizacao, usuario_operador, nucleo):
    evento = Evento.objects.create(
        titulo="Evento API",
        descricao="Teste de API",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua API, 123",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=1,
        numero_presentes=0,
        participantes_maximo=80,
        nucleo=nucleo,
    )

    api_client.force_authenticate(usuario_operador)

    list_url = reverse("eventos_api:evento-list")
    list_response = api_client.get(list_url)

    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json().get("results", [])}
    assert str(evento.id) in ids

    detail_url = reverse("eventos_api:evento-detail", args=[evento.pk])
    patch_response = api_client.patch(detail_url, {"titulo": "Evento API Atualizado"}, format="json")

    assert patch_response.status_code == 200
    evento.refresh_from_db()
    assert evento.titulo == "Evento API Atualizado"
