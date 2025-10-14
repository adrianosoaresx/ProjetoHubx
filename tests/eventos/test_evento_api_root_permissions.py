from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def root_user() -> User:
    return User.objects.create_user(
        username="root_user",
        email="root@example.com",
        password="pass",
        user_type=UserType.ROOT,
    )


@pytest.fixture
def organizacao() -> Organizacao:
    return Organizacao.objects.create(
        nome="Org Root",
        cnpj="00000000000191",
        slug="org-root",
    )


@pytest.fixture
def evento(organizacao: Organizacao) -> Evento:
    inicio = make_aware(datetime.now() + timedelta(days=1))
    fim = make_aware(datetime.now() + timedelta(days=2))
    return Evento.objects.create(
        titulo="Evento Root",
        descricao="Descricao",
        data_inicio=inicio,
        data_fim=fim,
        local="Rua Exemplo, 123",
        cidade="Cidade",
        estado="SC",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_convidados=10,
        valor_ingresso=Decimal("0.00"),
        participantes_maximo=100,
    )


@pytest.fixture
def associado(organizacao: Organizacao) -> User:
    return User.objects.create_user(
        username="associado",
        email="associado@example.com",
        password="pass",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
    )


@pytest.fixture
def inscricao(evento: Evento, associado: User) -> InscricaoEvento:
    return InscricaoEvento.objects.create(evento=evento, user=associado, status="confirmada")


def test_root_user_cannot_list_eventos(api_client: APIClient, root_user: User):
    api_client.force_authenticate(root_user)
    response = api_client.get(reverse("eventos_api:evento-list"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_root_user_cannot_create_eventos(api_client: APIClient, root_user: User):
    api_client.force_authenticate(root_user)
    response = api_client.post(reverse("eventos_api:evento-list"), data={}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_root_user_receives_empty_inscricoes(api_client: APIClient, root_user: User, inscricao: InscricaoEvento):
    api_client.force_authenticate(root_user)
    response = api_client.get(reverse("eventos_api:inscricao-list"))

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload.get("count") == 0
    assert payload.get("results") == []
