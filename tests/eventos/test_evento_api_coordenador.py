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
        nome="Org Eventos",
        cnpj="00000000000111",
        descricao="Organização para testes de eventos",
    )


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(organizacao=organizacao, nome="Núcleo Teste")


@pytest.fixture
def associado_coordenador(organizacao, nucleo):
    return User.objects.create_user(
        email="coord@example.com",
        username="coord",
        password="test-pass",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
        is_associado=True,
        nucleo=nucleo,
        is_coordenador=True,
    )


def _evento_payload(nucleo):
    inicio = make_aware(datetime.now() + timedelta(days=1))
    fim = make_aware(datetime.now() + timedelta(days=2))
    return {
        "titulo": "Novo evento",
        "descricao": "Descrição do evento",
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "local": "Rua X, 123",
        "cidade": "Florianópolis",
        "estado": "SC",
        "cep": "88000-000",
        "status": int(Evento.Status.ATIVO),
        "publico_alvo": 0,
        "nucleo": nucleo.pk,
    }


def test_associado_coordenador_nao_pode_criar_evento(api_client, associado_coordenador, nucleo):
    api_client.force_authenticate(user=associado_coordenador)

    response = api_client.post(
        reverse("eventos_api:evento-list"),
        data=_evento_payload(nucleo),
        format="json",
    )

    assert response.status_code == 403


def test_associado_coordenador_pode_editar_evento(api_client, associado_coordenador, organizacao, nucleo):
    evento = Evento.objects.create(
        titulo="Evento existente",
        descricao="Evento para edição",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Y, 456",
        cidade="Florianópolis",
        estado="SC",
        cep="88000-000",
        organizacao=organizacao,
        nucleo=nucleo,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
    )

    api_client.force_authenticate(user=associado_coordenador)

    response = api_client.patch(
        reverse("eventos_api:evento-detail", args=[evento.pk]),
        data={"titulo": "Evento atualizado"},
        format="json",
    )

    assert response.status_code == 200
    evento.refresh_from_db()
    assert evento.titulo == "Evento atualizado"
