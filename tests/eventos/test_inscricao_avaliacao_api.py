import pytest
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from eventos.factories import EventoFactory
from eventos.models import FeedbackNota, InscricaoEvento

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def test_avaliar_inscricao(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, nucleo_obj=None)
    evento = EventoFactory(
        coordenador=user,
        organizacao=org,
        nucleo=None,
        data_inicio=timezone.now() - timedelta(days=2),
        data_fim=timezone.now() - timedelta(days=1),
    )
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento, status="confirmada")
    api_client.force_authenticate(user)
    url = reverse("eventos_api:inscricao-avaliar", args=[inscricao.pk])
    resp = api_client.post(url, {"nota": 5, "feedback": "Ótimo"})
    assert resp.status_code == status.HTTP_200_OK
    feedback = FeedbackNota.objects.get(evento=evento, usuario=user)
    assert feedback.nota == 5
    assert feedback.comentario == "Ótimo"
    evento_url = reverse("eventos_api:evento-detail", args=[evento.pk])
    resp_evento = api_client.get(evento_url)
    assert resp_evento.status_code == status.HTTP_200_OK
    assert resp_evento.data["nota_media"] == 5
    assert resp_evento.data["distribuicao_notas"]["5"] == 1


def test_avaliar_inscricao_antes_evento(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, nucleo_obj=None)
    evento = EventoFactory(
        coordenador=user,
        organizacao=org,
        nucleo=None,
        data_inicio=timezone.now() + timedelta(days=1),
        data_fim=timezone.now() + timedelta(days=2),
    )
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento, status="confirmada")
    api_client.force_authenticate(user)
    url = reverse("eventos_api:inscricao-avaliar", args=[inscricao.pk])
    resp = api_client.post(url, {"nota": 4})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert not FeedbackNota.objects.filter(evento=evento, usuario=user).exists()


def test_reavaliar_inscricao(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = UserFactory(organizacao=org, nucleo_obj=None)
    evento = EventoFactory(
        coordenador=user,
        organizacao=org,
        nucleo=None,
        data_inicio=timezone.now() - timedelta(days=2),
        data_fim=timezone.now() - timedelta(days=1),
    )
    inscricao = InscricaoEvento.objects.create(user=user, evento=evento, status="confirmada")
    api_client.force_authenticate(user)
    url = reverse("eventos_api:inscricao-avaliar", args=[inscricao.pk])
    resp1 = api_client.post(url, {"nota": 5})
    assert resp1.status_code == status.HTTP_200_OK
    resp2 = api_client.post(url, {"nota": 4})
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    feedback = FeedbackNota.objects.get(evento=evento, usuario=user)
    assert feedback.nota == 5
