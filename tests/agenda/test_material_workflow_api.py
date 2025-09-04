import pytest
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from eventos.models import MaterialDivulgacaoEvento, EventoLog


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
def test_material_aprovar_devolver(api_client: APIClient) -> None:
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
    url_aprovar = reverse("agenda_api:material-aprovar", args=[material.pk])
    resp = api_client.post(url_aprovar)
    assert resp.status_code == status.HTTP_200_OK
    material.refresh_from_db()
    assert material.status == "aprovado"
    assert material.avaliado_por == user
    assert material.avaliado_em is not None
    assert EventoLog.objects.filter(evento=evento, acao="material_aprovado").exists()

    url_devolver = reverse("agenda_api:material-devolver", args=[material.pk])
    resp = api_client.post(url_devolver, {"motivo_devolucao": "erro"})
    assert resp.status_code == status.HTTP_200_OK
    material.refresh_from_db()
    assert material.status == "devolvido"
    assert material.motivo_devolucao == "erro"
    assert EventoLog.objects.filter(
        evento=evento,
        acao="material_devolvido",
        detalhes__motivo_devolucao="erro",
    ).exists()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_material_devolver_exige_motivo(api_client: APIClient) -> None:
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
    url = reverse("agenda_api:material-devolver", args=[material.pk])
    resp = api_client.post(url, {})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
