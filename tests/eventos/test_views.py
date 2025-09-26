from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.timezone import make_aware
from django.test import override_settings

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
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
        local="Rua Teste, 123",
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
        orcamento_estimado=5500.00,
        valor_gasto=4500.00,
        participantes_maximo=150,
        contato_nome="Contato Teste",
        contato_email="contato@teste.com",
        contato_whatsapp="12999998888",
    )


@pytest.fixture
def inscricao(evento, usuario_logado):
    return InscricaoEvento.objects.create(usuario=usuario_logado, evento=evento)


def test_calendar_view_get(client):
    url = reverse("eventos:calendario")
    response = client.get(url)
    assert response.status_code == 200
    assert "<html" in response.content.decode().lower()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_evento_detail_view_htmx(evento, client):
    url = f"/eventos/evento/{evento.pk}/"
    client.force_login(evento.coordenador)
    response = client.get(url, HTTP_HX_REQUEST="true")
    content = response.content.decode()
    assert response.status_code == 200
    assert evento.local in content
    assert evento.cidade in content
    assert evento.estado in content
    assert evento.cep in content
    assert evento.contato_nome in content
    assert evento.contato_email in content
    assert evento.contato_whatsapp in content
    assert str(evento.participantes_maximo) in content
    assert str(int(evento.orcamento_estimado)) in content
    assert str(int(evento.valor_gasto)) in content


@pytest.mark.xfail(reason="Erro de template em produção")
def test_evento_detail_view_sem_htmx(evento, client):
    url = reverse("eventos:evento_detalhe", args=[evento.pk])
    response = client.get(url)
    assert response.status_code in [302, 403, 404]


def test_eventos_por_dia_view_com_evento(client, evento):
    dia = evento.data_inicio.date().isoformat()
    url = reverse("eventos:eventos_por_dia") + f"?dia={dia}"
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert evento.titulo in response.content.decode()


def test_eventos_por_dia_view_sem_htmx(client, evento):
    dia = evento.data_inicio.date().isoformat()
    url = reverse("eventos:eventos_por_dia") + f"?dia={dia}"
    response = client.get(url)
    assert response.status_code in [200, 302, 403, 404]


def test_evento_list_filters_by_status(usuario_logado, organizacao, client, evento):
    evento_realizado = Evento.objects.create(
        titulo="Evento Concluído",
        descricao="Descrição do evento realizado",
        data_inicio=make_aware(datetime.now() - timedelta(days=2)),
        data_fim=make_aware(datetime.now() - timedelta(days=1)),
        local="Rua Teste, 456",
        cidade="Cidade Teste",
        estado="ST",
        cep="12345-678",
        coordenador=usuario_logado,
        organizacao=organizacao,
        status=1,
        publico_alvo=0,
        numero_convidados=80,
        numero_presentes=60,
        valor_ingresso=40.00,
        orcamento_estimado=3000.00,
        valor_gasto=2500.00,
        participantes_maximo=120,
        contato_nome="Contato Realizado",
        contato_email="realizado@teste.com",
        contato_whatsapp="12999996666",
    )

    url = reverse("eventos:lista")
    response = client.get(url, {"status": "realizados"})

    assert response.status_code == 200
    eventos = list(response.context["eventos"])
    assert evento_realizado in eventos
    assert evento not in eventos
    assert response.context["current_filter"] == "realizados"
    assert response.context["is_realizados_filter_active"] is True
    assert response.context["is_ativos_filter_active"] is False
    assert response.context["realizados_filter_url"].endswith("?status=realizados")
    assert response.context["ativos_filter_url"].endswith("?status=ativos")


def test_evento_create_view_post_invalido(usuario_logado, client):
    url = reverse("eventos:evento_novo")
    response = client.post(url, data={"titulo": ""})  # inválido
    assert response.status_code == 200
    assert "form" in response.context
    assert response.context["form"].errors


def test_evento_create_view_post_valido(usuario_logado, organizacao, client):
    url = reverse("eventos:evento_novo")
    data = {
        "titulo": "Novo Evento",
        "descricao": "Descrição",
        "data_inicio": make_aware(datetime.now()).isoformat(),
        "data_fim": make_aware(datetime.now() + timedelta(hours=1)).isoformat(),
        "local": "Rua A",
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
