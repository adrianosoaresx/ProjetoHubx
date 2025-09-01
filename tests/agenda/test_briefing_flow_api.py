import pytest
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from agenda.models import BriefingEvento, EventoLog


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
def test_briefing_orcamentar(api_client: APIClient) -> None:
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
    url = reverse("agenda_api:briefing-orcamentar", args=[briefing.pk])
    prazo = (timezone.now() + timezone.timedelta(days=5)).isoformat()
    resp = api_client.post(url, {"prazo_limite_resposta": prazo})
    assert resp.status_code == status.HTTP_200_OK
    briefing.refresh_from_db()
    assert briefing.status == "orcamentado"
    assert briefing.orcamento_enviado_em is not None
    assert briefing.prazo_limite_resposta.isoformat() == prazo
    assert EventoLog.objects.filter(evento=evento, acao="briefing_orcamentado").exists()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_briefing_aprovar(api_client: APIClient) -> None:
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
    url = reverse("agenda_api:briefing-aprovar", args=[briefing.pk])
    resp = api_client.post(url)
    assert resp.status_code == status.HTTP_200_OK
    briefing.refresh_from_db()
    assert briefing.status == "aprovado"
    assert briefing.aprovado_em is not None
    assert EventoLog.objects.filter(evento=evento, acao="briefing_aprovado").exists()


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_briefing_recusar(api_client: APIClient) -> None:
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
    url = reverse("agenda_api:briefing-recusar", args=[briefing.pk])
    motivo = "Sem verba"
    resp = api_client.post(url, {"motivo_recusa": motivo})
    assert resp.status_code == status.HTTP_200_OK
    briefing.refresh_from_db()
    assert briefing.status == "recusado"
    assert briefing.motivo_recusa == motivo
    assert briefing.recusado_por == user
    assert briefing.recusado_em is not None
    assert EventoLog.objects.filter(
        evento=evento,
        acao="briefing_recusado",
        detalhes__motivo_recusa=motivo,
    ).exists()
