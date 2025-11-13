import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from eventos.factories import EventoFactory
from eventos.models import Evento
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo


@pytest.mark.django_db
def test_coordenador_dashboard_routes_return_success(client):
    nucleo = NucleoFactory()
    user = UserFactory(user_type=UserType.COORDENADOR, organizacao=nucleo.organizacao)
    ParticipacaoNucleo.objects.create(
        user=user,
        nucleo=nucleo,
        papel="coordenador",
        papel_coordenador=ParticipacaoNucleo.PapelCoordenador.COORDENADOR_GERAL,
        status="ativo",
        status_suspensao=False,
    )
    EventoFactory(
        organizacao=nucleo.organizacao,
        nucleo=nucleo,
        status=Evento.Status.ATIVO,
    )

    client.force_login(user)

    response = client.get(reverse("dashboard:admin_dashboard"))
    assert response.status_code == 200
    response = client.get(reverse("dashboard:coordenador_dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_consultor_dashboard_routes_return_success(client):
    nucleo = NucleoFactory()
    user = UserFactory(user_type=UserType.CONSULTOR, organizacao=nucleo.organizacao)
    nucleo.consultor = user
    nucleo.save()
    EventoFactory(
        organizacao=nucleo.organizacao,
        nucleo=nucleo,
        status=Evento.Status.PLANEJAMENTO,
    )

    client.force_login(user)

    response = client.get(reverse("dashboard:admin_dashboard"))
    assert response.status_code == 200
    response = client.get(reverse("dashboard:consultor_dashboard"))
    assert response.status_code == 200
