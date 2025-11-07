from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware

from accounts.models import User, UserType
from eventos.models import Evento, InscricaoEvento
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
        local="Rua Teste, 123",
        cidade="Cidade Teste",
        estado="ST",
        cep="12345-678",
        organizacao=organizacao,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=100,
        valor_associado=Decimal("129.90"),
        valor_nucleado=Decimal("79.90"),
    )


@pytest.fixture
def usuario_comum(client, organizacao):
    user = User.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="12345",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
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
def operador(organizacao):
    return User.objects.create_user(
        username="operador",
        email="operador@example.com",
        password="12345",
        user_type=UserType.OPERADOR,
        organizacao=organizacao,
    )


@pytest.fixture
def usuario_associado(client, organizacao):
    user = User.objects.create_user(
        username="associado",
        email="associado@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
    )
    client.force_login(user)
    return user


@pytest.fixture
def inscricao(evento, usuario_logado):
    return InscricaoEvento.objects.create(user=usuario_logado, evento=evento)


def test_evento_detail_htmx(evento, client):
    """TODO revisar template de detalhe de evento."""
    pytest.skip("Template de evento não disponível")


def test_usuario_pode_inscrever_e_cancelar(evento, usuario_comum, client):
    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])

    # Inscreve
    resp1 = client.post(subscribe_url)
    assert resp1.status_code == 302
    inscricao = InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="confirmada").first()
    assert inscricao is not None
    assert inscricao.valor_pago == evento.get_valor_para_usuario(usuario_comum)

    # Cancela
    resp2 = client.post(cancel_url)
    assert resp2.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()
    assert (
        InscricaoEvento.all_objects.filter(
            evento=evento,
            user=usuario_comum,
            status="cancelada",
            deleted=True,
        ).count()
        == 1
    )


def test_gerente_pode_remover_inscrito(evento, usuario_comum, gerente, client):
    evento.organizacao = gerente.organizacao
    evento.save()
    InscricaoEvento.objects.create(evento=evento, user=usuario_comum, status="confirmada")

    client.force_login(gerente)
    url = reverse("eventos:evento_remover_inscrito", args=[evento.pk, usuario_comum.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()


def test_operador_pode_remover_inscrito(evento, usuario_comum, operador, client):
    evento.organizacao = operador.organizacao
    evento.save()
    InscricaoEvento.objects.create(evento=evento, user=usuario_comum, status="confirmada")

    client.force_login(operador)
    url = reverse("eventos:evento_remover_inscrito", args=[evento.pk, usuario_comum.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()


def test_admin_pode_editar_inscricao(evento, usuario_logado, client, organizacao):
    outro_usuario = User.objects.create_user(
        username="participante",
        email="participante@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=outro_usuario,
        status="confirmada",
    )
    url = reverse("eventos:inscricao_editar", args=[inscricao.pk])

    response_get = client.get(url)
    assert response_get.status_code == 200

    response_post = client.post(
        url,
        {
            "valor_pago": "123.45",
            "metodo_pagamento": "pix",
        },
    )
    assert response_post.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.valor_pago == evento.get_valor_para_usuario(outro_usuario)
    assert inscricao.metodo_pagamento == "pix"


def test_admin_pode_definir_faturamento_parcelado(
    evento, usuario_logado, client, organizacao
):
    outro_usuario = User.objects.create_user(
        username="participante-faturar",
        email="participante-faturar@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=outro_usuario,
        status="confirmada",
    )
    url = reverse("eventos:inscricao_editar", args=[inscricao.pk])

    valor_evento = evento.get_valor_para_usuario(outro_usuario) or Decimal("0.00")

    response_post = client.post(
        url,
        {
            "valor_pago": f"{valor_evento:.2f}",
            "metodo_pagamento": "faturar_2x",
        },
    )

    assert response_post.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.metodo_pagamento == "faturar_2x"
    assert inscricao.valor_pago == valor_evento


def test_admin_pode_validar_pagamento(evento, usuario_logado, client, organizacao):
    participante = User.objects.create_user(
        username="participante-validacao",
        email="participante-validacao@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=participante,
        status="confirmada",
        metodo_pagamento="pix",
    )

    url = reverse("eventos:inscricao_toggle_validacao", args=[inscricao.pk])
    response = client.post(url)

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.pagamento_validado is True


def test_validacao_pagamento_htmx(evento, usuario_logado, client, organizacao):
    participante = User.objects.create_user(
        username="participante-htmx",
        email="participante-htmx@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=participante,
        status="confirmada",
        metodo_pagamento="pix",
    )

    url = reverse("eventos:inscricao_toggle_validacao", args=[inscricao.pk])
    response = client.post(url, HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    assert b"Validado" in response.content


def test_nao_permite_validacao_de_outra_organizacao(evento, usuario_logado, client):
    outra_org = Organizacao.objects.create(nome="Outra Org", cnpj="12345678000199")
    outro_evento = Evento.objects.create(
        titulo="Outro Evento",
        descricao="Outro",
        data_inicio=make_aware(datetime.now() + timedelta(days=3)),
        data_fim=make_aware(datetime.now() + timedelta(days=4)),
        local="Rua B",
        cidade="Cidade B",
        estado="ST",
        cep="00000-000",
        organizacao=outra_org,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
        numero_presentes=0,
        participantes_maximo=10,
        valor_associado=Decimal("50.00"),
        valor_nucleado=Decimal("40.00"),
    )
    participante = User.objects.create_user(
        username="externo",
        email="externo@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=outra_org,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=outro_evento,
        user=participante,
        status="confirmada",
    )

    url = reverse("eventos:inscricao_toggle_validacao", args=[inscricao.pk])
    response = client.post(url)

    assert response.status_code == 403
    inscricao.refresh_from_db()
    assert inscricao.pagamento_validado is False


def test_usuario_sem_permissao_nao_valida(evento, usuario_comum, client):
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=usuario_comum,
        status="confirmada",
    )

    url = reverse("eventos:inscricao_toggle_validacao", args=[inscricao.pk])
    response = client.post(url)

    assert response.status_code == 403
    inscricao.refresh_from_db()
    assert inscricao.pagamento_validado is False


def test_admin_ve_acoes_de_inscricao_no_detalhe(evento, usuario_logado, client, organizacao):
    participante = User.objects.create_user(
        username="inscrito",
        email="inscrito@example.com",
        password="12345",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=participante,
        status="confirmada",
    )
    detail_url = reverse("eventos:evento_detalhe", args=[evento.pk])
    response = client.get(detail_url)
    assert response.status_code == 200
    assert reverse("eventos:inscricao_editar", args=[inscricao.pk]) in response.content.decode()
    remover_url = reverse("eventos:evento_remover_inscrito", args=[evento.pk, participante.pk])
    assert remover_url in response.content.decode()


def test_operador_tem_contexto_para_gerenciar_inscricoes(evento, client, operador):
    evento.organizacao = operador.organizacao
    evento.save()
    client.force_login(operador)
    detail_url = reverse("eventos:evento_detalhe", args=[evento.pk])
    response = client.get(detail_url)
    assert response.status_code == 200
    assert response.context["pode_gerenciar_inscricoes"] is True


def test_confirmar_inscricao(inscricao):
    inscricao.confirmar_inscricao()
    assert inscricao.status == "confirmada"
    assert inscricao.data_confirmacao is not None


def test_cancelar_inscricao(inscricao):
    inscricao.cancelar_inscricao()
    assert inscricao.status == "cancelada"
    assert inscricao.deleted is True


def test_cancelar_inscricao_apos_inicio_model(inscricao):
    inscricao.evento.data_inicio = make_aware(datetime.now() - timedelta(hours=1))
    inscricao.evento.save(update_fields=["data_inicio"])
    with pytest.raises(ValueError):
        inscricao.cancelar_inscricao()
    inscricao.refresh_from_db()
    assert inscricao.status != "cancelada"


def test_usuario_nao_pode_cancelar_apos_inicio(evento, usuario_comum, client):
    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])
    client.post(subscribe_url)
    evento.data_inicio = make_aware(datetime.now() - timedelta(hours=1))
    evento.save(update_fields=["data_inicio"])
    resp = client.post(cancel_url)
    assert resp.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="confirmada").exists()


def test_usuario_nao_pode_inscrever_evento_inativo(evento, usuario_comum, client):
    evento.status = Evento.Status.CANCELADO
    evento.save(update_fields=["status"])
    url = reverse("eventos:evento_subscribe", args=[evento.pk])

    resp = client.post(url)

    assert resp.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_comum).exists()


def test_usuario_nao_pode_cancelar_evento_inativo(evento, usuario_comum, client):
    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])
    client.post(subscribe_url)
    assert InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="confirmada").exists()

    evento.status = Evento.Status.CONCLUIDO
    evento.save(update_fields=["status"])

    resp = client.post(cancel_url)

    assert resp.status_code == 302
    assert InscricaoEvento.objects.filter(evento=evento, user=usuario_comum, status="confirmada").exists()


def test_qrcode_and_checkin(client, inscricao):
    inscricao.confirmar_inscricao()
    assert inscricao.qrcode_url
    url = reverse("eventos:inscricao_checkin", args=[inscricao.pk])
    timestamp = int(inscricao.created_at.timestamp())
    codigo = f"inscricao:{inscricao.pk}:{timestamp}"
    resp = client.post(url, {"codigo": codigo})
    assert resp.status_code == 200
    inscricao.refresh_from_db()
    assert inscricao.check_in_realizado_em is not None


def test_realizar_check_in_incrementa_numero_presentes(evento, inscricao):
    inscricao.confirmar_inscricao()
    inscricao.realizar_check_in()
    evento.refresh_from_db()
    assert evento.numero_presentes == 1


def test_cancelar_inscricao_decrementa_numero_presentes(evento, inscricao):
    inscricao.confirmar_inscricao()
    inscricao.realizar_check_in()
    evento.refresh_from_db()
    assert evento.numero_presentes == 1
    inscricao.cancelar_inscricao()
    evento.refresh_from_db()
    assert evento.numero_presentes == 0


def test_cancelar_remove_associado_da_lista(evento, usuario_associado, client):
    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])
    detail_url = reverse("eventos:evento_detalhe", args=[evento.pk])

    response_subscribe = client.post(subscribe_url)
    assert response_subscribe.status_code == 302
    assert (
        InscricaoEvento.objects.filter(evento=evento, user=usuario_associado, status="confirmada")
        .filter(deleted=False)
        .exists()
    )

    response_cancel = client.post(cancel_url)
    assert response_cancel.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_associado).exists()

    client.force_login(usuario_associado)
    detail_response = client.get(detail_url)
    assert detail_response.status_code == 200
    assert not detail_response.context["inscricoes_confirmadas"]
    assert detail_response.context["inscricao"] is None


def test_associado_pode_reinscrever_apos_cancelar(evento, usuario_associado, client):
    subscribe_url = reverse("eventos:evento_subscribe", args=[evento.pk])
    cancel_url = reverse("eventos:evento_cancelar_inscricao", args=[evento.pk])

    first_subscribe = client.post(subscribe_url)
    assert first_subscribe.status_code == 302

    cancel_response = client.post(cancel_url)
    assert cancel_response.status_code == 302
    assert not InscricaoEvento.objects.filter(evento=evento, user=usuario_associado).exists()
    assert (
        InscricaoEvento.all_objects.filter(evento=evento, user=usuario_associado, status="cancelada")
        .filter(deleted=True)
        .count()
        == 1
    )

    second_subscribe = client.post(subscribe_url)
    assert second_subscribe.status_code == 302
    assert (
        InscricaoEvento.objects.filter(evento=evento, user=usuario_associado, status="confirmada")
        .filter(deleted=False)
        .count()
        == 1
    )
    assert (
        InscricaoEvento.all_objects.filter(evento=evento, user=usuario_associado)
        .filter(deleted=False)
        .count()
        == 1
    )
