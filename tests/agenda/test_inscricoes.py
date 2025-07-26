from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org Teste", cnpj="00000000000191")


@pytest.fixture
def usuario_logado(client, organizacao):
    user = User.objects.create_user(
        username="logado",
        email="logado@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.ADMIN,
    )
    client.force_login(user)
    return user


@pytest.fixture
def evento(organizacao, usuario_logado):
    return Evento.objects.create(
        titulo="Evento Teste",
        descricao="Descrição do evento",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        endereco="Rua Teste, 123",
        cidade="Cidade Teste",
        estado="ST",
        cep="12345-678",
        coordenador=usuario_logado,
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_convidados=100,
        numero_presentes=0,
        valor_ingresso=50.00,
        orcamento=5000.00,
    )


@pytest.fixture
def usuario_comum(client):
    user = User.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="12345",
        user_type=UserType.NUCLEADO,
    )
    client.force_login(user)
    return user


@pytest.fixture
def gerente(organizacao):
    return User.objects.create_user(
        username="gerente",
        email="gerente@example.com",
        password="12345",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )


@pytest.fixture
def inscricao(evento, usuario_logado):
    return InscricaoEvento.objects.create(user=usuario_logado, evento=evento)


def test_evento_detail_htmx(evento, client):
    """TODO revisar template de detalhe de evento."""
    pytest.skip("Template de evento não disponível")


def test_usuario_pode_inscrever_e_cancelar(evento, usuario_comum, client):
    url = reverse("agenda:evento_subscribe", args=[evento.pk])

    # Inscreve
    resp1 = client.post(url)
    assert resp1.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="confirmada").exists()

    # Cancela
    resp2 = client.post(url)
    assert resp2.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="cancelada").exists()


def test_gerente_pode_remover_inscrito(evento, usuario_comum, gerente, client):
    evento.organizacao = gerente.organizacao
    evento.save()
    InscricaoEvento.objects.create(evento=evento, user=usuario_comum, status="confirmada")

    client.force_login(gerente)
    url = reverse("agenda:evento_remover_inscrito", args=[evento.pk, usuario_comum.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()


def test_confirmar_inscricao(inscricao):
    inscricao.confirmar_inscricao()
    assert inscricao.status == "confirmada"
    assert inscricao.data_confirmacao is not None


def test_cancelar_inscricao(inscricao):
    inscricao.cancelar_inscricao()
    assert inscricao.status == "cancelada"


def test_qrcode_and_checkin(client, inscricao):
    inscricao.confirmar_inscricao()
    assert inscricao.qrcode_url
    url = reverse("agenda:inscricao_checkin", args=[inscricao.pk])
    codigo = f"inscricao:{inscricao.pk}:{int(inscricao.created_at.timestamp())}"
    resp = client.post(url, {"codigo": codigo})
    assert resp.status_code == 200
    inscricao.refresh_from_db()
    assert inscricao.check_in_realizado_em is not None
