from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao
from nucleos.models import Nucleo, ParticipacaoNucleo

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
def usuario_operador(organizacao):
    return User.objects.create_user(
        username="operador",
        email="operador@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.OPERADOR,
    )


@pytest.fixture
def nucleo(organizacao):
    return Nucleo.objects.create(organizacao=organizacao, nome="Núcleo Restrito")


@pytest.fixture
def usuario_coordenador(organizacao, nucleo):
    user = User.objects.create_user(
        username="coordenador",
        email="coordenador@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
        is_associado=True,
        is_coordenador=True,
        nucleo=nucleo,
    )
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=nucleo,
        status="ativo",
        papel="coordenador",
        papel_coordenador=ParticipacaoNucleo.PapelCoordenador.EVENTOS,
    )
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
        organizacao=organizacao,
        status=Evento.Status.PLANEJAMENTO,
        publico_alvo=0,
        numero_presentes=0,
        orcamento_estimado=5500.00,
        valor_gasto=4500.00,
        participantes_maximo=150,
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
def test_evento_detail_view_htmx(evento, client, usuario_logado):
    url = f"/eventos/evento/{evento.pk}/"
    client.force_login(usuario_logado)
    response = client.get(url, HTTP_HX_REQUEST="true")
    content = response.content.decode()
    assert response.status_code == 200
    assert evento.local in content
    assert evento.cidade in content
    assert evento.estado in content
    assert evento.cep in content
    assert str(evento.participantes_maximo) in content
    assert str(int(evento.orcamento_estimado)) in content
    assert str(int(evento.valor_gasto)) in content


def test_evento_detail_admin_sees_edit_button(evento, client, usuario_logado):
    url = reverse("eventos:evento_detalhe", args=[evento.pk])
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert reverse("eventos:evento_editar", args=[evento.pk]) in response.content.decode()


def test_evento_detail_non_admin_hides_edit_button(evento, client, usuario_comum):
    url = reverse("eventos:evento_detalhe", args=[evento.pk])
    response = client.get(url, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert reverse("eventos:evento_editar", args=[evento.pk]) not in response.content.decode()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_evento_detail_nucleado_sem_coordenacao_oculta_campos(
    client, organizacao, nucleo
):
    briefing = SimpleUploadedFile("briefing.pdf", b"briefing", content_type="application/pdf")
    parcerias = SimpleUploadedFile("parcerias.pdf", b"parcerias", content_type="application/pdf")
    evento_restrito = Evento.objects.create(
        titulo="Evento Restrito",
        descricao="Somente para nucleados",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Teste, 456",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=nucleo,
        status=Evento.Status.ATIVO,
        publico_alvo=1,
        numero_presentes=0,
        participantes_maximo=40,
        briefing=briefing,
        parcerias=parcerias,
    )

    usuario_nucleado = User.objects.create_user(
        username="nucleado",
        email="nucleado@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO,
        is_associado=True,
        nucleo=nucleo,
    )
    ParticipacaoNucleo.objects.create(
        user=usuario_nucleado,
        nucleo=nucleo,
        status="ativo",
        papel="membro",
    )

    client.force_login(usuario_nucleado)
    response = client.get(
        reverse("eventos:evento_detalhe", args=[evento_restrito.pk]),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Máximo de participantes" not in content
    assert "Briefing" not in content
    assert "Parcerias" not in content


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_evento_detail_coordenador_visualiza_campos_restritos(
    client, organizacao, nucleo, usuario_coordenador
):
    briefing = SimpleUploadedFile("briefing.pdf", b"briefing", content_type="application/pdf")
    parcerias = SimpleUploadedFile("parcerias.pdf", b"parcerias", content_type="application/pdf")
    evento_restrito = Evento.objects.create(
        titulo="Evento Coordenado",
        descricao="Apenas coordenador",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Teste, 789",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=nucleo,
        status=Evento.Status.ATIVO,
        publico_alvo=1,
        numero_presentes=0,
        participantes_maximo=55,
        briefing=briefing,
        parcerias=parcerias,
    )

    client.force_login(usuario_coordenador)
    response = client.get(
        reverse("eventos:evento_detalhe", args=[evento_restrito.pk]),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Máximo de participantes" in content
    assert "Briefing" in content
    assert "Parcerias" in content


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
        organizacao=organizacao,
        status=Evento.Status.CONCLUIDO,
        publico_alvo=0,
        numero_presentes=60,
        orcamento_estimado=3000.00,
        valor_gasto=2500.00,
        participantes_maximo=120,
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
    assert response.context["is_planejamento_filter_active"] is False
    assert response.context["realizados_filter_url"].endswith("?status=realizados")
    assert response.context["ativos_filter_url"].endswith("?status=ativos")
    assert response.context["planejamento_filter_url"].endswith("?status=planejamento")


def test_evento_list_filters_by_planejamento(usuario_logado, organizacao, client, evento):
    evento_planejamento = evento
    evento_planejamento.status = Evento.Status.PLANEJAMENTO
    evento_planejamento.save(update_fields=["status"])

    evento_ativo = Evento.objects.create(
        titulo="Evento Ativo",
        descricao="Descrição do evento ativo",
        data_inicio=make_aware(datetime.now() + timedelta(days=2)),
        data_fim=make_aware(datetime.now() + timedelta(days=3)),
        local="Rua Teste, 789",
        cidade="Cidade Teste",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        orcamento_estimado=2500.00,
        valor_gasto=2000.00,
        participantes_maximo=90,
    )

    url = reverse("eventos:lista")
    response = client.get(url, {"status": "planejamento"})

    assert response.status_code == 200
    eventos = list(response.context["eventos"])
    assert evento_planejamento in eventos
    assert evento_ativo not in eventos
    assert response.context["current_filter"] == "planejamento"
    assert response.context["is_planejamento_filter_active"] is True
    assert response.context["is_ativos_filter_active"] is False
    assert response.context["is_realizados_filter_active"] is False


def test_evento_list_filters_by_planejamento(usuario_logado, organizacao, client):
    evento_planejado = Evento.objects.create(
        titulo="Evento Planejado",
        descricao="Evento futuro",
        data_inicio=make_aware(datetime.now() + timedelta(days=5)),
        data_fim=make_aware(datetime.now() + timedelta(days=6)),
        local="Rua Futuro, 789",
        cidade="Cidade Futuro",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=80,
    )
    Evento.objects.create(
        titulo="Evento Passado",
        descricao="Evento não planejado",
        data_inicio=make_aware(datetime.now() - timedelta(days=5)),
        data_fim=make_aware(datetime.now() - timedelta(days=4)),
        local="Rua Passado, 101",
        cidade="Cidade Passado",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=80,
    )

    url = reverse("eventos:lista")
    response = client.get(url, {"status": "planejamento"})

    assert response.status_code == 200
    eventos = list(response.context["eventos"])
    assert evento_planejado in eventos
    assert len(eventos) == 1
    assert response.context["current_filter"] == "planejamento"
    assert response.context["is_planejamento_filter_active"] is True
    assert response.context["planejamento_filter_url"].endswith("?status=planejamento")
    assert response.context["total_eventos_planejamento"] == 1


def test_evento_list_filters_by_cancelados(usuario_logado, organizacao, client):
    evento_cancelado = Evento.objects.create(
        titulo="Evento Cancelado",
        descricao="Evento cancelado",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Cancelada, 202",
        cidade="Cidade Cancelada",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=2,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=60,
    )
    Evento.objects.create(
        titulo="Evento Ativo",
        descricao="Evento ativo",
        data_inicio=make_aware(datetime.now() + timedelta(days=3)),
        data_fim=make_aware(datetime.now() + timedelta(days=4)),
        local="Rua Ativa, 303",
        cidade="Cidade Ativa",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=0,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=60,
    )

    url = reverse("eventos:lista")
    response = client.get(url, {"status": "cancelados"})

    assert response.status_code == 200
    eventos = list(response.context["eventos"])
    assert eventos == [evento_cancelado]
    assert response.context["current_filter"] == "cancelados"
    assert response.context["is_cancelados_filter_active"] is True
    assert response.context["cancelados_filter_url"].endswith("?status=cancelados")
    assert response.context["total_eventos_cancelados"] == 1


def test_evento_list_consultor_restringe_planejamento_cancelados(organizacao, client):
    consultor = User.objects.create_user(
        username="consultor",
        email="consultor@example.com",
        password="12345",
        organizacao=organizacao,
        user_type=UserType.CONSULTOR,
    )
    nucleo_consultoria = Nucleo.objects.create(
        organizacao=organizacao,
        nome="Núcleo Consultoria",
        consultor=consultor,
    )
    outro_nucleo = Nucleo.objects.create(
        organizacao=organizacao,
        nome="Outro Núcleo",
    )

    evento_planejamento_visivel = Evento.objects.create(
        titulo="Planejado visível",
        descricao="Evento do meu núcleo",
        data_inicio=make_aware(datetime.now() + timedelta(days=5)),
        data_fim=make_aware(datetime.now() + timedelta(days=6)),
        local="Rua Principal, 123",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=nucleo_consultoria,
        status=Evento.Status.PLANEJAMENTO,
        publico_alvo=0,
        numero_presentes=0,
    )
    Evento.objects.create(
        titulo="Planejado oculto",
        descricao="Evento de outro núcleo",
        data_inicio=make_aware(datetime.now() + timedelta(days=7)),
        data_fim=make_aware(datetime.now() + timedelta(days=8)),
        local="Rua Secundária, 456",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=outro_nucleo,
        status=Evento.Status.PLANEJAMENTO,
        publico_alvo=0,
        numero_presentes=0,
    )

    evento_cancelado_visivel = Evento.objects.create(
        titulo="Cancelado visível",
        descricao="Cancelado do meu núcleo",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Cancelada, 789",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=nucleo_consultoria,
        status=Evento.Status.CANCELADO,
        publico_alvo=0,
        numero_presentes=0,
    )
    evento_cancelado_oculto = Evento.objects.create(
        titulo="Cancelado oculto",
        descricao="Cancelado de outro núcleo",
        data_inicio=make_aware(datetime.now() + timedelta(days=3)),
        data_fim=make_aware(datetime.now() + timedelta(days=4)),
        local="Rua Oculta, 321",
        cidade="Cidade",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=outro_nucleo,
        status=Evento.Status.CANCELADO,
        publico_alvo=0,
        numero_presentes=0,
    )

    client.force_login(consultor)
    response = client.get(reverse("eventos:lista"))

    assert response.status_code == 200
    planejamento_qs = list(response.context["eventos_planejamento"])
    cancelados_qs = list(response.context["eventos_cancelados"])

    assert response.context["can_view_planejamento_cancelados"] is True
    assert evento_planejamento_visivel in planejamento_qs
    assert all(evento.nucleo_id == nucleo_consultoria.id for evento in planejamento_qs)
    assert evento_cancelado_visivel in cancelados_qs
    assert evento_cancelado_oculto not in cancelados_qs
    assert all(evento.nucleo_id == nucleo_consultoria.id for evento in cancelados_qs)
    assert response.context["total_eventos_planejamento"] == 1
    assert response.context["total_eventos_cancelados"] == 1


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
        "status": 0,
        "publico_alvo": 0,
        "participantes_maximo": 10,
    }
    response = client.post(url, data=data, follow=True)
    assert response.status_code == 200
    assert Evento.objects.filter(titulo="Novo Evento").exists()


def test_operador_lista_eventos_restritos(client, organizacao, usuario_operador, nucleo):
    evento_restrito = Evento.objects.create(
        titulo="Evento Restrito",
        descricao="Somente para teste",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Teste, 456",
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

    client.force_login(usuario_operador)
    response = client.get(reverse("eventos:lista"))

    assert response.status_code == 200
    eventos = list(response.context["eventos"])
    assert evento_restrito in eventos


def test_operador_acessa_edicao_evento(client, organizacao, usuario_operador, nucleo):
    evento_restrito = Evento.objects.create(
        titulo="Evento Para Edição",
        descricao="Somente para teste",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Teste, 456",
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

    client.force_login(usuario_operador)
    url = reverse("eventos:evento_editar", args=[evento_restrito.pk])
    response = client.get(url)

    assert response.status_code == 200
    assert "Editar Evento" in response.content.decode()


def test_evento_update_redirects_to_detail(client, organizacao, usuario_operador, nucleo):
    evento_nucleo = _criar_evento(organizacao, nucleo)
    client.force_login(usuario_operador)

    url = reverse("eventos:evento_editar", args=[evento_nucleo.pk])
    data = {
        "titulo": "Evento Atualizado",
        "descricao": "Descrição do evento",
        "data_inicio": evento_nucleo.data_inicio.isoformat(),
        "data_fim": evento_nucleo.data_fim.isoformat(),
        "local": evento_nucleo.local,
        "cidade": evento_nucleo.cidade,
        "estado": evento_nucleo.estado,
        "cep": evento_nucleo.cep,
        "status": str(evento_nucleo.status),
        "publico_alvo": str(evento_nucleo.publico_alvo),
        "nucleo": "",
        "participantes_maximo": evento_nucleo.participantes_maximo or "",
        "cronograma": "",
        "informacoes_adicionais": "",
        "briefing": "",
        "parcerias": "",
    }

    response = client.post(url, data=data)

    assert response.status_code == 302
    assert response["Location"] == reverse("eventos:evento_detalhe", args=[evento_nucleo.pk])


def _criar_evento(
    organizacao,
    nucleo,
    titulo="Evento Núcleo",
    *,
    publico_alvo=0,
):
    return Evento.objects.create(
        titulo=titulo,
        descricao="Descrição do evento",
        data_inicio=make_aware(datetime.now() + timedelta(days=1)),
        data_fim=make_aware(datetime.now() + timedelta(days=2)),
        local="Rua Exemplo, 123",
        cidade="Cidade",
        estado="SP",
        cep="12345-678",
        organizacao=organizacao,
        nucleo=nucleo,
        status=Evento.Status.PLANEJAMENTO,
        publico_alvo=publico_alvo,
        numero_presentes=0,
        participantes_maximo=10,
    )


def test_coordenador_edita_evento_do_proprio_nucleo(client, organizacao, nucleo, usuario_coordenador):
    evento_nucleo = _criar_evento(organizacao, nucleo)
    client.force_login(usuario_coordenador)

    url = reverse("eventos:evento_editar", args=[evento_nucleo.pk])
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert evento_nucleo.titulo in content
    assert "Editar Evento" in content


def test_coordenador_bloqueado_em_evento_de_outro_nucleo(client, organizacao, nucleo, usuario_coordenador):
    outro_nucleo = Nucleo.objects.create(organizacao=organizacao, nome="Outro Núcleo")
    evento_outro = _criar_evento(organizacao, outro_nucleo, titulo="Outro", publico_alvo=1)
    client.force_login(usuario_coordenador)

    url = reverse("eventos:evento_editar", args=[evento_outro.pk])
    response = client.get(url)

    assert response.status_code in {403, 404}
