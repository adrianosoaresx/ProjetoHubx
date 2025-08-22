import pytest
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from agenda.factories import EventoFactory
from agenda.models import BriefingEvento, EventoLog


@pytest.mark.django_db
def test_aprovar_briefing(client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    client.force_login(user)
    evento = EventoFactory(organizacao=org, coordenador=user)
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
        status="orcamentado",
    )
    url = reverse("agenda:briefing_status", args=[briefing.pk, "aprovado"])
    with patch("agenda.views.notificar_briefing_status.delay") as mock_delay:
        response = client.post(url)
    assert response.status_code == 302
    briefing.refresh_from_db()
    assert briefing.status == "aprovado"
    assert briefing.avaliado_por == user
    assert briefing.aprovado_em is not None
    assert EventoLog.objects.filter(evento=evento, acao="briefing_aprovado").exists()
    mock_delay.assert_called_once_with(briefing.pk, "aprovado")


@pytest.mark.django_db
def test_orcamentar_briefing(client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    client.force_login(user)
    evento = EventoFactory(organizacao=org, coordenador=user)
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
    )
    url = reverse("agenda:briefing_status", args=[briefing.pk, "orcamentado"])
    prazo = (timezone.now() + timezone.timedelta(days=5)).isoformat()
    with patch("agenda.views.notificar_briefing_status.delay") as mock_delay:
        response = client.post(url, {"prazo_limite_resposta": prazo})
    assert response.status_code == 302
    briefing.refresh_from_db()
    assert briefing.status == "orcamentado"
    assert briefing.prazo_limite_resposta.isoformat() == prazo
    assert briefing.orcamento_enviado_em is not None
    assert EventoLog.objects.filter(evento=evento, acao="briefing_orcamentado").exists()
    mock_delay.assert_called_once_with(briefing.pk, "orcamentado")


@pytest.mark.django_db
def test_recusar_briefing_com_motivo(client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    client.force_login(user)
    evento = EventoFactory(organizacao=org, coordenador=user)
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
        status="orcamentado",
    )
    url = reverse("agenda:briefing_status", args=[briefing.pk, "recusado"])
    motivo = "Sem orçamento"
    with patch("agenda.views.notificar_briefing_status.delay") as mock_delay:
        response = client.post(url, {"motivo_recusa": motivo})
    assert response.status_code == 302
    briefing.refresh_from_db()
    assert briefing.status == "recusado"
    assert briefing.motivo_recusa == motivo
    assert briefing.recusado_por == user
    assert briefing.recusado_em is not None
    assert EventoLog.objects.filter(evento=evento, acao="briefing_recusado").exists()
    mock_delay.assert_called_once_with(briefing.pk, "recusado")


@pytest.mark.django_db
def test_transicao_fora_de_ordem(client):
    org = OrganizacaoFactory()
    user = UserFactory(user_type=UserType.ADMIN, organizacao=org)
    client.force_login(user)
    evento = EventoFactory(organizacao=org, coordenador=user)
    briefing = BriefingEvento.objects.create(
        evento=evento,
        objetivos="obj",
        publico_alvo="pub",
        requisitos_tecnicos="req",
    )
    url = reverse("agenda:briefing_status", args=[briefing.pk, "aprovado"])
    resp = client.post(url)
    briefing.refresh_from_db()
    assert briefing.status == "rascunho"
    msgs = [m.message for m in get_messages(resp.wsgi_request)]
    assert "Transição de status inválida." in msgs
