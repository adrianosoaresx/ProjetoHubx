import pytest
from datetime import date
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.factories import UserFactory
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from agenda.models import ParceriaEvento
from accounts.models import UserType


@pytest.mark.django_db
def test_non_admin_cannot_create_briefing():
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ASSOCIADO, organizacao=evento.organizacao, nucleo_obj=None)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("agenda_api:briefing-list")
    data = {"evento": evento.pk, "objetivos": "o", "publico_alvo": "p", "requisitos_tecnicos": "r"}
    resp = client.post(url, data)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_can_create_briefing():
    evento = EventoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("agenda_api:briefing-list")
    data = {"evento": evento.pk, "objetivos": "o", "publico_alvo": "p", "requisitos_tecnicos": "r"}
    resp = client.post(url, data)
    assert resp.status_code == 201


@pytest.mark.django_db
def test_unauthenticated_request_denied():
    evento = EventoFactory()
    client = APIClient()
    url = reverse("agenda_api:briefing-list")
    resp = client.get(url)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_avaliar_parceria_ja_avaliada_retorna_erro():
    evento = EventoFactory()
    empresa = EmpresaFactory(organizacao=evento.organizacao)
    parceria = ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        nucleo=evento.nucleo,
        cnpj="12345678901234",
        contato="Contato",
        representante_legal="Rep",
        data_inicio=date.today(),
        data_fim=date.today(),
        avaliacao=5,
    )
    user = UserFactory(user_type=UserType.ADMIN, organizacao=evento.organizacao, nucleo_obj=None)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("agenda_api:parceria-avaliar", args=[parceria.pk])
    resp = client.post(url, {"avaliacao": 4})
    assert resp.status_code == 400
    assert resp.json()["error"] == "Parceria já avaliada."
