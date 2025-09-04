import time
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import UserType
from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from empresas.factories import EmpresaFactory
from agenda.factories import EventoFactory
from eventos.models import (
    BriefingEvento,
    EventoLog,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
)
from validate_docbr import CNPJ

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _admin_user(organizacao):
    return UserFactory(
        organizacao=organizacao,
        user_type=UserType.ADMIN,
        is_superuser=True,
        is_staff=True,
        nucleo_obj=None,
    )


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_parceria_create_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    empresa = EmpresaFactory(organizacao=org, usuario=user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:parceria-list")
    data = {
        "evento": evento.pk,
        "empresa": empresa.pk,
        "cnpj": CNPJ().generate(),
        "contato": "c",
        "representante_legal": "r",
        "data_inicio": date.today(),
        "data_fim": date.today() + timedelta(days=1),
        "tipo_parceria": "patrocinio",
    }
    resp = api_client.post(url, data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    parceria_id = resp.data["id"]
    assert EventoLog.objects.filter(
        evento=evento,
        usuario=user,
        acao="parceria_criada",
        detalhes__parceria=parceria_id,
        detalhes__empresa=empresa.pk,
    ).exists()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_parceria_avaliar_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    empresa = EmpresaFactory(organizacao=org, usuario=user)
    parceria = ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        cnpj="12345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=1),
        tipo_parceria="patrocinio",
    )
    api_client.force_authenticate(user)
    url = reverse("agenda_api:parceria-avaliar", args=[parceria.pk])
    resp = api_client.post(url, {"avaliacao": 4, "comentario": "Bom"})
    assert resp.status_code == status.HTTP_200_OK
    assert EventoLog.objects.filter(
        evento=evento,
        usuario=user,
        acao="parceria_avaliada",
        detalhes__parceria=parceria.pk,
        detalhes__avaliacao=4,
        detalhes__comentario="Bom",
    ).exists()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_parceria_delete_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    empresa = EmpresaFactory(organizacao=org, usuario=user)
    parceria = ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        cnpj="12345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=1),
        tipo_parceria="patrocinio",
    )
    api_client.force_authenticate(user)
    url = reverse("agenda_api:parceria-detail", args=[parceria.pk])
    api_client.delete(url)
    assert EventoLog.objects.filter(
        evento=evento,
        usuario=user,
        acao="parceria_excluida",
        detalhes__parceria=parceria.pk,
        detalhes__empresa=parceria.empresa_id,
    ).exists()


def test_material_delete_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    arquivo = SimpleUploadedFile("m.pdf", b"%PDF-1.4")
    material = MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="M",
        tipo="banner",
        arquivo=arquivo,
    )
    api_client.force_authenticate(user)
    url = reverse("agenda_api:material-detail", args=[material.pk])
    api_client.delete(url)
    assert EventoLog.objects.filter(
        evento=evento,
        usuario=user,
        acao="material_excluido",
        detalhes__material=material.pk,
    ).exists()


def test_briefing_delete_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
    )
    api_client.force_authenticate(user)
    url = reverse("agenda_api:briefing-detail", args=[briefing.pk])
    api_client.delete(url)
    assert EventoLog.objects.filter(
        evento=evento,
        usuario=user,
        acao="briefing_excluido",
        detalhes__briefing=briefing.pk,
    ).exists()


def test_evento_update_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user, titulo="Antigo")
    api_client.force_authenticate(user)
    url = reverse("agenda_api:evento-detail", args=[evento.pk])
    resp = api_client.patch(url, {"titulo": "Novo"}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    log = EventoLog.objects.get(evento=evento, acao="evento_atualizado")
    assert log.detalhes["titulo"] == {"antes": "Antigo", "depois": "Novo"}


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_parceria_update_gera_log(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    evento = EventoFactory(organizacao=org, coordenador=user)
    empresa = EmpresaFactory(organizacao=org, usuario=user)
    parceria = ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        cnpj="12345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=1),
        tipo_parceria="patrocinio",
    )
    api_client.force_authenticate(user)
    url = reverse("agenda_api:parceria-detail", args=[parceria.pk])
    resp = api_client.patch(url, {"tipo_parceria": "mentoria"}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    log = EventoLog.objects.get(evento=evento, acao="parceria_atualizada")
    assert log.detalhes["tipo_parceria"] == {
        "antes": "patrocinio",
        "depois": "mentoria",
    }


def test_evento_list_performance(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    EventoFactory.create_batch(5, organizacao=org, coordenador=user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:evento-list")
    durations = []
    for _ in range(20):
        start = time.perf_counter()
        api_client.get(url)
        durations.append(time.perf_counter() - start)
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 <= 0.3
