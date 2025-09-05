import pytest
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from empresas.factories import EmpresaFactory
from eventos.factories import EventoFactory
from eventos.models import InscricaoEvento, ParceriaEvento


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _user(organizacao, user_type=UserType.ASSOCIADO):
    return UserFactory(organizacao=organizacao, user_type=user_type, nucleo_obj=None)


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_avaliar_evento(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _user(org)
    evento = EventoFactory(
        organizacao=org,
        coordenador=user,
        data_inicio=timezone.now() - timezone.timedelta(days=2),
        data_fim=timezone.now() - timezone.timedelta(days=1),
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=user,
        status="confirmada",
        data_confirmacao=timezone.now(),
        presente=True,
    )
    api_client.force_authenticate(user)
    url = reverse("eventos_api:inscricao-avaliar", args=[inscricao.pk])
    resp = api_client.post(url, {"nota": 4, "feedback": "bom"})
    assert resp.status_code == status.HTTP_200_OK
    inscricao.refresh_from_db()
    assert inscricao.avaliacao == 4
    assert inscricao.feedback == "bom"


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_avaliar_evento_antes_do_fim(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _user(org)
    evento = EventoFactory(
        organizacao=org,
        coordenador=user,
        data_inicio=timezone.now() + timezone.timedelta(hours=1),
        data_fim=timezone.now() + timezone.timedelta(days=1),
    )
    inscricao = InscricaoEvento.objects.create(
        evento=evento,
        user=user,
        status="confirmada",
        data_confirmacao=timezone.now(),
        presente=False,
    )
    api_client.force_authenticate(user)
    url = reverse("eventos_api:inscricao-avaliar", args=[inscricao.pk])
    resp = api_client.post(url, {"nota": 5})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_avaliar_parceria(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    admin = _user(org, UserType.ADMIN)
    evento = EventoFactory(organizacao=org, coordenador=admin)
    empresa = EmpresaFactory(organizacao=org, usuario=admin)
    parceria = ParceriaEvento.objects.create(
        evento=evento,
        empresa=empresa,
        cnpj="12345678000199",
        contato="c",
        representante_legal="r",
        data_inicio=timezone.now().date(),
        data_fim=timezone.now().date(),
        tipo_parceria="patrocinio",
    )
    api_client.force_authenticate(admin)
    url = reverse("eventos_api:parceria-avaliar", args=[parceria.pk])
    resp = api_client.post(url, {"avaliacao": 5, "comentario": "ok"})
    assert resp.status_code == status.HTTP_200_OK
    parceria.refresh_from_db()
    assert parceria.avaliacao == 5
    assert parceria.comentario == "ok"

