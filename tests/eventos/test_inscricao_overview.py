import os
from datetime import timedelta

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


User = get_user_model()


def _create_organizacao() -> Organizacao:
    return Organizacao.objects.create(nome="Org", cnpj="12345678000195")


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
        "titulo": "Evento",
        "slug": f"evento-{timezone.now().timestamp()}",
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
        "gratuito": True,
        "participantes_maximo": 10,
    }
    defaults.update(kwargs)
    return Evento.objects.create(**defaults)


@pytest.mark.django_db
def test_overview_uses_subscribe_endpoint_for_free_events() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "associado_overview")
    evento = _create_evento(organizacao, slug="evento-overview")

    client = Client()
    client.force_login(usuario)
    response = client.get(reverse("eventos:inscricao_overview", kwargs={"pk": evento.pk}))

    assert response.status_code == 200
    assert response.context["cta_url"] == reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk})
    assert f'action="{reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk})}"' in response.content.decode()


@pytest.mark.django_db
def test_subscribe_keeps_confirmed_subscription() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "associado_confirmado")
    evento = _create_evento(organizacao, slug="evento-confirmado")
    inscricao = InscricaoEvento.all_objects.create(user=usuario, evento=evento, status="confirmada")

    client = Client()
    client.force_login(usuario)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.status == "confirmada"
    assert InscricaoEvento.all_objects.filter(user=usuario, evento=evento).count() == 1


@pytest.mark.django_db
def test_subscribe_confirms_pending_subscription() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "associado_pendente")
    evento = _create_evento(organizacao, slug="evento-pendente")
    inscricao = InscricaoEvento.all_objects.create(user=usuario, evento=evento, status="pendente")

    client = Client()
    client.force_login(usuario)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.status == "confirmada"
    assert inscricao.deleted is False


@pytest.mark.django_db
def test_subscribe_reactivates_soft_deleted_subscription_and_confirms() -> None:
    organizacao = _create_organizacao()
    usuario = _create_user(organizacao, "associado_soft_deleted")
    evento = _create_evento(organizacao, slug="evento-soft-deleted")
    inscricao = InscricaoEvento.all_objects.create(user=usuario, evento=evento, status="cancelada")
    inscricao.delete()

    client = Client()
    client.force_login(usuario)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao.refresh_from_db()
    assert inscricao.deleted is False
    assert inscricao.status == "confirmada"


@pytest.mark.django_db
def test_subscribe_soft_deletes_new_subscription_when_event_is_full() -> None:
    organizacao = _create_organizacao()
    confirmado = _create_user(organizacao, "associado_lotado_ok")
    candidato = _create_user(organizacao, "associado_lotado_fail")
    evento = _create_evento(organizacao, slug="evento-lotado", participantes_maximo=1)
    InscricaoEvento.all_objects.create(user=confirmado, evento=evento, status="confirmada")

    client = Client()
    client.force_login(candidato)
    response = client.post(reverse("eventos:evento_subscribe", kwargs={"pk": evento.pk}))

    assert response.status_code == 302
    inscricao = InscricaoEvento.all_objects.get(user=candidato, evento=evento)
    assert inscricao.deleted is True
    assert inscricao.status == "pendente"
