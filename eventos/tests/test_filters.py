from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from eventos.factories import EventoFactory
from eventos.models import Evento
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.fixture
def eventos_dataset(db):
    organizacao = OrganizacaoFactory()
    outra_organizacao = OrganizacaoFactory()
    nucleo_principal = NucleoFactory(organizacao=organizacao)
    outro_nucleo = NucleoFactory(organizacao=organizacao)
    nucleo_outra_org = NucleoFactory(organizacao=outra_organizacao)

    now = timezone.now()
    later = now + timedelta(hours=2)

    eventos = {
        "publico_geral_ativo": EventoFactory(
            organizacao=organizacao,
            nucleo=None,
            status=Evento.Status.ATIVO,
            publico_alvo=0,
            data_inicio=now,
            data_fim=later,
        ),
        "publico_geral_cancelado": EventoFactory(
            organizacao=organizacao,
            nucleo=None,
            status=Evento.Status.CANCELADO,
            publico_alvo=0,
            data_inicio=now,
            data_fim=later,
        ),
        "nucleo_ativo": EventoFactory(
            organizacao=organizacao,
            nucleo=nucleo_principal,
            status=Evento.Status.ATIVO,
            publico_alvo=1,
            data_inicio=now,
            data_fim=later,
        ),
        "nucleo_cancelado": EventoFactory(
            organizacao=organizacao,
            nucleo=nucleo_principal,
            status=Evento.Status.CANCELADO,
            publico_alvo=1,
            data_inicio=now,
            data_fim=later,
        ),
        "outro_nucleo": EventoFactory(
            organizacao=organizacao,
            nucleo=outro_nucleo,
            status=Evento.Status.ATIVO,
            publico_alvo=1,
            data_inicio=now,
            data_fim=later,
        ),
        "publico_associados": EventoFactory(
            organizacao=organizacao,
            nucleo=None,
            status=Evento.Status.ATIVO,
            publico_alvo=2,
            data_inicio=now,
            data_fim=later,
        ),
        "outra_org": EventoFactory(
            organizacao=outra_organizacao,
            nucleo=nucleo_outra_org,
            status=Evento.Status.ATIVO,
            publico_alvo=0,
            data_inicio=now,
            data_fim=later,
        ),
    }

    return {
        "organizacao": organizacao,
        "nucleo_principal": nucleo_principal,
        "eventos": eventos,
    }


def _criar_associado(organizacao, *, nucleo=None, is_coordenador=False):
    user = UserFactory(
        organizacao=organizacao,
        user_type=UserType.ASSOCIADO.value,
        is_associado=True,
        nucleo=nucleo,
        is_coordenador=is_coordenador,
    )
    user.set_password("teste123")
    user.nucleo = nucleo
    user.is_coordenador = is_coordenador
    user.save()
    if nucleo is not None:
        ParticipacaoNucleo.objects.create(
            user=user,
            nucleo=nucleo,
            status="ativo",
            papel="coordenador" if is_coordenador else "membro",
            papel_coordenador=(
                ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL
                if is_coordenador
                else None
            ),
        )
    return user


def _ids_eventos(response):
    return {str(event.pk) for event in response.context["eventos"]}


def test_evento_list_view_associado_sem_nucleo_exibe_apenas_publicos_ativos(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=None)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("eventos:lista"))
    assert response.status_code == 200

    eventos_visiveis = _ids_eventos(response)
    esperado = {str(eventos_dataset["eventos"]["publico_geral_ativo"].pk)}
    assert eventos_visiveis == esperado


def test_evento_list_view_nucleado_verifica_publicos_e_do_nucleo(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=eventos_dataset["nucleo_principal"], is_coordenador=False)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("eventos:lista"))
    assert response.status_code == 200

    eventos_visiveis = _ids_eventos(response)
    esperados = {
        str(eventos_dataset["eventos"]["publico_geral_ativo"].pk),
        str(eventos_dataset["eventos"]["publico_geral_cancelado"].pk),
        str(eventos_dataset["eventos"]["nucleo_ativo"].pk),
        str(eventos_dataset["eventos"]["nucleo_cancelado"].pk),
    }
    assert eventos_visiveis == esperados


def test_evento_list_view_coordenador_verifica_publicos_e_do_nucleo(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=eventos_dataset["nucleo_principal"], is_coordenador=True)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("eventos:lista"))
    assert response.status_code == 200

    eventos_visiveis = _ids_eventos(response)
    esperados = {
        str(eventos_dataset["eventos"]["publico_geral_ativo"].pk),
        str(eventos_dataset["eventos"]["publico_geral_cancelado"].pk),
        str(eventos_dataset["eventos"]["nucleo_ativo"].pk),
        str(eventos_dataset["eventos"]["nucleo_cancelado"].pk),
    }
    assert eventos_visiveis == esperados


def _ids_api(response):
    payload = response.json()
    return {item["id"] for item in payload.get("results", payload)}


def test_evento_api_lista_associado_sem_nucleo_filtra_publicos_ativos(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=None)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("eventos_api:evento-list"))
    assert response.status_code == 200
    eventos_visiveis = _ids_api(response)
    esperado = {str(eventos_dataset["eventos"]["publico_geral_ativo"].pk)}
    assert eventos_visiveis == esperado


def test_evento_api_lista_nucleado_inclui_eventos_do_nucleo(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=eventos_dataset["nucleo_principal"], is_coordenador=False)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("eventos_api:evento-list"))
    assert response.status_code == 200
    eventos_visiveis = _ids_api(response)
    esperados = {
        str(eventos_dataset["eventos"]["publico_geral_ativo"].pk),
        str(eventos_dataset["eventos"]["publico_geral_cancelado"].pk),
        str(eventos_dataset["eventos"]["nucleo_ativo"].pk),
        str(eventos_dataset["eventos"]["nucleo_cancelado"].pk),
    }
    assert eventos_visiveis == esperados


def test_evento_api_lista_coordenador_inclui_eventos_do_nucleo(eventos_dataset):
    user = _criar_associado(eventos_dataset["organizacao"], nucleo=eventos_dataset["nucleo_principal"], is_coordenador=True)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("eventos_api:evento-list"))
    assert response.status_code == 200
    eventos_visiveis = _ids_api(response)
    esperados = {
        str(eventos_dataset["eventos"]["publico_geral_ativo"].pk),
        str(eventos_dataset["eventos"]["publico_geral_cancelado"].pk),
        str(eventos_dataset["eventos"]["nucleo_ativo"].pk),
        str(eventos_dataset["eventos"]["nucleo_cancelado"].pk),
    }
    assert eventos_visiveis == esperados
