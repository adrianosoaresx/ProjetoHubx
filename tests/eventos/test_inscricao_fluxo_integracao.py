import os
from datetime import timedelta
from decimal import Decimal

import django
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()

from accounts.models import UserType
from eventos.models import Evento, InscricaoEvento
from organizacoes.models import Organizacao
from pagamentos.models import Pedido, Transacao

User = get_user_model()


def _create_organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Org Fluxo", cnpj="12345678000195")


def _create_user(organizacao: Organizacao, username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="senha123",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


def _create_evento(organizacao: Organizacao, **kwargs) -> Evento:
    inicio = timezone.now() + timedelta(days=2)
    defaults = {
        "titulo": "Evento Fluxo",
        "slug": f"evento-fluxo-{timezone.now().timestamp()}",
        "descricao": "Descricao",
        "data_inicio": inicio,
        "data_fim": inicio + timedelta(hours=2),
        "local": "Local",
        "cidade": "Cidade",
        "estado": "SP",
        "cep": "12345-678",
        "organizacao": organizacao,
        "status": Evento.Status.ATIVO,
        "publico_alvo": 0,
        "participantes_maximo": 10,
    }
    defaults.update(kwargs)
    return Evento.objects.create(**defaults)


def _create_transacao(organizacao: Organizacao, status: str) -> Transacao:
    pedido = Pedido.objects.create(
        organizacao=organizacao,
        valor=Decimal("150.00"),
        status=Pedido.Status.PENDENTE,
    )
    return Transacao.objects.create(
        pedido=pedido,
        metodo=Transacao.Metodo.PIX,
        valor=Decimal("150.00"),
        status=status,
    )


@pytest.mark.django_db
def test_fluxo_gratuito_confirma_e_redireciona_para_resultado() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "assoc_gratuito")
    evento = _create_evento(organizacao, gratuito=True)

    client = Client()
    client.force_login(usuario)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert reverse("eventos:inscricao_resultado", kwargs={"uuid": inscricao.uuid}) in response.url
    assert inscricao.status == "confirmada"


@pytest.mark.django_db
def test_fluxo_pago_sem_comprovante_permanece_pendente() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "assoc_pago_sem_comp")
    evento = _create_evento(
        organizacao,
        gratuito=False,
        valor_associado=Decimal("150.00"),
    )

    client = Client()
    client.force_login(usuario)
    response = client.post(
        reverse("eventos:inscricao_criar", kwargs={"pk": evento.pk}),
        data={"metodo_pagamento": "pix"},
    )

    assert response.status_code == 302
    inscricao = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert inscricao.status == "pendente"
    assert "status=info" in response.url


@pytest.mark.django_db
def test_fluxo_pago_checkout_com_transacao_aprovada_confirma() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "assoc_pago_aprovado")
    evento = _create_evento(
        organizacao,
        gratuito=False,
        valor_associado=Decimal("150.00"),
    )
    transacao = _create_transacao(organizacao, Transacao.Status.APROVADA)

    client = Client()
    client.force_login(usuario)
    response = client.post(
        reverse("eventos:inscricao_pagamentos_criar", kwargs={"pk": evento.pk}),
        data={
            "metodo_pagamento": "pix",
            "transacao_id": transacao.pk,
        },
    )

    assert response.status_code == 302
    inscricao = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert inscricao.status == "confirmada"
    assert inscricao.transacao_id == transacao.pk
    assert reverse("eventos:inscricao_resultado", kwargs={"uuid": inscricao.uuid}) in response.url


@pytest.mark.django_db
def test_fluxo_pago_checkout_com_transacao_pendente_permanece_pendente() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "assoc_pago_pendente")
    evento = _create_evento(
        organizacao,
        gratuito=False,
        valor_associado=Decimal("150.00"),
    )
    transacao = _create_transacao(organizacao, Transacao.Status.PENDENTE)

    client = Client()
    client.force_login(usuario)
    response = client.post(
        reverse("eventos:inscricao_pagamentos_criar", kwargs={"pk": evento.pk}),
        data={
            "metodo_pagamento": "pix",
            "transacao_id": transacao.pk,
        },
    )

    assert response.status_code == 302
    inscricao = InscricaoEvento.all_objects.get(user=usuario, evento=evento)
    assert inscricao.status == "pendente"
    assert inscricao.transacao_id == transacao.pk
    assert "status=info" in response.url


@pytest.mark.django_db
def test_reinscricao_apos_cancelamento_reativa_soft_delete() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "assoc_reinscricao")
    evento = _create_evento(organizacao, gratuito=True)
    inscricao = InscricaoEvento.all_objects.create(user=usuario, evento=evento, status="cancelada")
    inscricao.delete()

    client = Client()
    client.force_login(usuario)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.deleted is False
    assert inscricao.status == "confirmada"
    assert reverse("eventos:inscricao_resultado", kwargs={"uuid": inscricao.uuid}) in response.url
