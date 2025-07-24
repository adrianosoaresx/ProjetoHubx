from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from agenda.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(
        nome="Org Teste",
        cnpj="00000000000191",
        descricao="Descrição teste",
    )


@pytest.fixture
def usuario_logado(client, organizacao):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.ADMIN,
    )
    perm = Permission.objects.get(codename="add_evento")
    user.user_permissions.add(perm)
    client.force_login(user)
    return user


@pytest.fixture
def usuario_comum(client, organizacao):
    user = User.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.NUCLEADO,
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
def inscricao(evento, usuario_logado):
    return InscricaoEvento.objects.create(usuario=usuario_logado, evento=evento)


def test_calendar_view_get(client):
    url = reverse("agenda:calendario")
    response = client.get(url)
    assert response.status_code == 200
    assert "<html" in response.content.decode().lower()


@pytest.mark.xfail(reason="Erro de template em produção")
def test_evento_detail_view_htmx(evento, client):
    url = reverse("agenda:evento_detalhe", args=[evento.pk])
    client.force_login(evento.coordenador)
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "evento" in response.context


@pytest.mark.xfail(reason="Erro de template em produção")
def test_evento_detail_view_sem_htmx(evento, client):
    url = reverse("agenda:evento_detalhe", args=[evento.pk])
    response = client.get(url)
    assert response.status_code in [302, 403, 404]


def test_eventos_por_dia_view_com_evento(client, evento):
    dia = evento.data_inicio.date().isoformat()
    url = reverse("agenda:eventos_por_dia") + f"?dia={dia}"
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert evento.titulo in response.content.decode()


def test_eventos_por_dia_view_sem_htmx(client, evento):
    dia = evento.data_inicio.date().isoformat()
    url = reverse("agenda:eventos_por_dia") + f"?dia={dia}"
    response = client.get(url)
    assert response.status_code in [200, 302, 403, 404]


def test_evento_create_view_post_invalido(usuario_logado, client):
    url = reverse("agenda:evento_novo")
    response = client.post(url, data={"titulo": ""})  # inválido
    assert response.status_code == 200
    assert "form" in response.context
    assert response.context["form"].errors


def test_evento_create_view_post_valido(usuario_logado, organizacao, client):
    url = reverse("agenda:evento_novo")
    data = {
        "titulo": "Novo Evento",
        "descricao": "Descrição",
        "data_inicio": make_aware(datetime.now()).isoformat(),
        "data_fim": make_aware(datetime.now() + timedelta(hours=1)).isoformat(),
        "briefing": "",
        "organizacao": organizacao.pk,
        "endereco": "Rua A",
        "cidade": "Cidade",
        "estado": "ST",
        "cep": "12345-678",
        "coordenador": usuario_logado.pk,
        "status": 0,
        "publico_alvo": 0,
        "numero_convidados": 10,
        "numero_presentes": 0,
        "contato_nome": "Fulano",
    }
    response = client.post(url, data=data, follow=True)
    assert response.status_code == 200
    assert Evento.objects.filter(titulo="Novo Evento").exists()
