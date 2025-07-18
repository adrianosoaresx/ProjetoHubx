from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, TipoUsuario
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")


@pytest.fixture
def evento(organizacao, usuario_comum):
    return Evento.objects.create(
        organizacao=organizacao,
        titulo="Evento Público",
        descricao="Aberto a inscrições",
        data_inicio=make_aware(datetime(2025, 7, 20, 14, 0)),
        data_fim=make_aware(datetime(2025, 7, 20, 16, 0)),
        briefing="",
        coordenador=usuario_comum,
    )


@pytest.fixture
def usuario_comum(client):
    user = User.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="12345",
        tipo_id=TipoUsuario.CLIENTE.value,
    )
    client.force_login(user)
    return user


@pytest.fixture
def gerente(organizacao):
    return User.objects.create_user(
        username="gerente",
        email="gerente@example.com",
        password="12345",
        tipo_id=User.Tipo.GERENTE,
        organizacao=organizacao,
    )


@pytest.fixture
def inscricao(evento, usuario_comum):
    return InscricaoEvento.objects.create(
        usuario=usuario_comum,
        evento=evento,
        status="pendente",
    )


def test_evento_detail_htmx(evento, client):
    url = reverse("agenda:evento_detalhe", args=[evento.pk])
    client.force_login(evento.organizacao.user_set.first())
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert evento.titulo in response.content.decode()


def test_usuario_pode_inscrever_e_cancelar(evento, usuario_comum, client):
    url = reverse("agenda:evento_subscribe", args=[evento.pk])

    # Inscreve
    resp1 = client.post(url)
    assert resp1.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, usuario=usuario_comum, status="confirmada").exists()

    # Cancela
    resp2 = client.post(url)
    assert resp2.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, usuario=usuario_comum, status="cancelada").exists()


def test_gerente_pode_remover_inscrito(evento, usuario_comum, gerente, client):
    evento.organizacao = gerente.organizacao
    evento.save()
    InscricaoEvento.objects.create(evento=evento, usuario=usuario_comum, status="confirmada")

    client.force_login(gerente)
    url = reverse("agenda:evento_remover_inscrito", args=[evento.pk, usuario_comum.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, usuario=usuario_comum).exists()


def test_confirmar_inscricao(inscricao):
    inscricao.confirmar_inscricao()
    assert inscricao.status == "confirmada"
    assert inscricao.data_confirmacao is not None


def test_cancelar_inscricao(inscricao):
    inscricao.cancelar_inscricao()
    assert inscricao.status == "cancelada"
