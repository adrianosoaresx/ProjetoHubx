from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")


@pytest.fixture
def usuario(client, organizacao):
    user = User.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="12345",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )
    client.force_login(user)
    return user


def criar_evento(organizacao, usuario, inicio, fim):
    return Evento.objects.create(
        organizacao=organizacao,
        titulo="Evento",
        descricao="Desc",
        data_inicio=inicio,
        data_fim=fim,
        briefing="",
        coordenador=usuario,
        status=0,
        publico_alvo=1,
        numero_convidados=50,
        numero_presentes=30,
    )


def test_avaliacao_permitida_pos_evento(client, usuario, organizacao):
    evento = criar_evento(
        organizacao,
        usuario,
        timezone.now() - timedelta(days=1),
        timezone.now() - timedelta(hours=1),
    )
    InscricaoEvento.objects.create(
        evento=evento,
        user=usuario,
        status="confirmada",
        data_confirmacao=timezone.now(),
        presente=False,
    )
    response = client.get(reverse("agenda:evento_detalhe", args=[evento.pk]))
    assert response.status_code == 200
    assert response.context["avaliacao_permitida"] is True
    assert "Avaliar evento" in response.content.decode()


def test_avaliacao_negada_evento_future(client, usuario, organizacao):
    evento = criar_evento(
        organizacao,
        usuario,
        timezone.now() + timedelta(hours=1),
        timezone.now() + timedelta(days=1),
    )
    InscricaoEvento.objects.create(
        evento=evento,
        user=usuario,
        status="confirmada",
        data_confirmacao=timezone.now(),
        presente=False,
    )
    response = client.get(reverse("agenda:evento_detalhe", args=[evento.pk]))
    assert response.status_code == 200
    assert response.context["avaliacao_permitida"] is False
    assert "Avaliar evento" not in response.content.decode()
