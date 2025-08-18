import re
from datetime import date
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from agenda.factories import EventoFactory
from empresas.factories import EmpresaFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True


def test_evento_delete_requires_admin_or_coordenador(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    creator = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    evento = EventoFactory(organizacao=org, coordenador=creator)
    url = reverse("agenda_api:evento-detail", args=[evento.pk])

    usuario = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org, nucleo_obj=None)
    api_client.force_authenticate(usuario)
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    for utype in [UserType.ADMIN, UserType.COORDENADOR]:
        user = UserFactory(user_type=utype, organizacao=org, nucleo_obj=None)
        evento = EventoFactory(organizacao=org, coordenador=user)
        api_client.force_authenticate(user)
        resp = api_client.delete(reverse("agenda_api:evento-detail", args=[evento.pk]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT


def test_parceria_create_requires_admin_or_coordenador(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    creator = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    evento = EventoFactory(organizacao=org, coordenador=creator)
    empresa = EmpresaFactory(organizacao=org, usuario=creator)
    url = reverse("agenda_api:parceria-list")
    data = {
        "evento": evento.id,
        "empresa": empresa.id,
        "cnpj": re.sub(r"\D", "", empresa.cnpj),
        "contato": "Fulano",
        "representante_legal": "Beltrano",
        "data_inicio": date.today(),
        "data_fim": date.today(),
        "tipo_parceria": "patrocinio",
    }
    usuario = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org, nucleo_obj=None)
    api_client.force_authenticate(usuario)
    resp = api_client.post(url, data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    for utype in [UserType.ADMIN, UserType.COORDENADOR]:
        user = UserFactory(user_type=utype, organizacao=org, nucleo_obj=None)
        api_client.force_authenticate(user)
        resp = api_client.post(url, data)
        assert resp.status_code == status.HTTP_201_CREATED


def test_material_create_requires_admin_or_coordenador(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    creator = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    evento = EventoFactory(organizacao=org, coordenador=creator)
    url = reverse("agenda_api:material-list")
    file_content = b"%PDF-1.4"
    data_base = {
        "evento": evento.id,
        "titulo": "Mat",
        "tipo": "banner",
    }
    usuario = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org, nucleo_obj=None)
    api_client.force_authenticate(usuario)
    file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
    resp = api_client.post(url, {**data_base, "arquivo": file}, format="multipart")
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    for utype in [UserType.ADMIN, UserType.COORDENADOR]:
        user = UserFactory(user_type=utype, organizacao=org, nucleo_obj=None)
        api_client.force_authenticate(user)
        file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
        with patch("agenda.serializers.upload_material_divulgacao.delay"):
            resp = api_client.post(url, {**data_base, "arquivo": file}, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED


def test_briefing_create_requires_admin_or_coordenador(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    creator = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    evento = EventoFactory(organizacao=org, coordenador=creator)
    url = reverse("agenda_api:briefing-list")
    data = {
        "evento": evento.id,
        "objetivos": "obj",
        "publico_alvo": "pub",
        "requisitos_tecnicos": "req",
    }
    usuario = UserFactory(user_type=UserType.ASSOCIADO, organizacao=org, nucleo_obj=None)
    api_client.force_authenticate(usuario)
    resp = api_client.post(url, data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    for utype in [UserType.ADMIN, UserType.COORDENADOR]:
        user = UserFactory(user_type=utype, organizacao=org, nucleo_obj=None)
        api_client.force_authenticate(user)
        resp = api_client.post(url, data)
        assert resp.status_code == status.HTTP_201_CREATED
