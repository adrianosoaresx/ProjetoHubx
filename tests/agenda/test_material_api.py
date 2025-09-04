import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from eventos.models import MaterialDivulgacaoEvento, EventoLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _create_material(user):
    evento = EventoFactory(organizacao=user.organizacao, coordenador=user)
    arquivo = SimpleUploadedFile("m.pdf", b"%PDF-1.4")
    material = MaterialDivulgacaoEvento.objects.create(
        evento=evento,
        titulo="M",
        tipo="banner",
        arquivo=arquivo,
    )
    return material


def test_aprovar_material(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    material = _create_material(user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:material-aprovar", args=[material.pk])
    resp = api_client.post(url)
    assert resp.status_code == status.HTTP_200_OK
    material.refresh_from_db()
    assert material.status == "aprovado"
    assert material.avaliado_por == user
    assert material.avaliado_em is not None
    assert material.motivo_devolucao == ""
    assert EventoLog.objects.filter(evento=material.evento, acao="material_aprovado", usuario=user).exists()


def test_devolver_material(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    material = _create_material(user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:material-devolver", args=[material.pk])
    resp = api_client.post(url, {"motivo_devolucao": "corrigir"})
    assert resp.status_code == status.HTTP_200_OK
    material.refresh_from_db()
    assert material.status == "devolvido"
    assert material.avaliado_por == user
    assert material.avaliado_em is not None
    assert material.motivo_devolucao == "corrigir"
    assert EventoLog.objects.filter(
        evento=material.evento,
        acao="material_devolvido",
        usuario=user,
        detalhes__motivo_devolucao="corrigir",
    ).exists()


def test_devolver_material_sem_motivo(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org, nucleo_obj=None)
    material = _create_material(user)
    api_client.force_authenticate(user)
    url = reverse("agenda_api:material-devolver", args=[material.pk])
    resp = api_client.post(url)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    material.refresh_from_db()
    assert material.status == "criado"
    assert material.motivo_devolucao == ""
    assert not EventoLog.objects.filter(
        evento=material.evento,
        acao="material_devolvido",
        usuario=user,
    ).exists()
