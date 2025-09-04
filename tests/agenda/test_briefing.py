import pytest
from unittest.mock import patch
from django.urls import reverse

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from accounts.models import UserType
from agenda.factories import EventoFactory
from agenda.models import BriefingEvento, EventoLog


@pytest.mark.django_db
def test_briefing_status_updates(client):
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
    with patch("eventos.views.notificar_briefing_status.delay") as mock_delay:
        response = client.post(url)
    assert response.status_code == 302
    briefing.refresh_from_db()
    assert briefing.status == "aprovado"
    assert briefing.avaliado_por == user
    assert briefing.avaliado_em is not None
    assert briefing.aprovado_em is not None
    assert briefing.coordenadora_aprovou is True
    assert EventoLog.objects.filter(evento=evento, acao="briefing_aprovado").exists()
    mock_delay.assert_called_once_with(briefing.pk, "aprovado")
