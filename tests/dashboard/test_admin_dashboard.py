import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from eventos.factories import EventoFactory
from eventos.models import Evento, InscricaoEvento
from dashboard.services import (
    ASSOCIADOS_NAO_NUCLEADOS_LABEL,
    ASSOCIADOS_NUCLEADOS_LABEL,
    EVENTOS_PUBLICOS_LABEL,
)
from dashboard.views import AdminDashboardView
from nucleos.factories import NucleoFactory
from nucleos.models import ParticipacaoNucleo
from organizacoes.factories import OrganizacaoFactory


@pytest.mark.django_db
def test_admin_dashboard_returns_expected_metrics():
    rf = RequestFactory()
    organizacao = OrganizacaoFactory()
    nucleo = NucleoFactory(organizacao=organizacao)

    admin_user = UserFactory(user_type=UserType.ADMIN, organizacao=organizacao)

    associado = UserFactory(organizacao=organizacao, is_associado=True)
    nucleado = UserFactory(organizacao=organizacao, is_associado=True)
    ParticipacaoNucleo.objects.create(user=nucleado, nucleo=nucleo, status="ativo")

    evento_ativo = EventoFactory(organizacao=organizacao, nucleo=nucleo, status=Evento.Status.ATIVO)
    EventoFactory(organizacao=organizacao, nucleo=nucleo, status=Evento.Status.CONCLUIDO)
    EventoFactory(organizacao=organizacao, nucleo=nucleo, status=Evento.Status.PLANEJAMENTO)
    EventoFactory(
        organizacao=organizacao,
        nucleo=None,
        status=Evento.Status.ATIVO,
        publico_alvo=0,
    )

    InscricaoEvento.objects.create(evento=evento_ativo, user=associado, status="confirmada")

    request = rf.get(reverse("dashboard:admin_dashboard"))
    request.user = admin_user
    response = AdminDashboardView.as_view()(request)

    assert response.status_code == 200
    context = response.context_data
    assert context["total_associados"] == 2
    assert context["total_nucleados"] == 1
    assert context["inscricoes_confirmadas"] == 1

    event_totals = context["eventos_por_status"]
    assert event_totals[Evento.Status.ATIVO.label] == 2
    assert event_totals[Evento.Status.CONCLUIDO.label] == 1
    assert event_totals[Evento.Status.PLANEJAMENTO.label] == 1

    eventos_chart = context["eventos_chart"]
    assert eventos_chart["total"] == 4

    eventos_por_nucleo = context["eventos_por_nucleo"]
    assert eventos_por_nucleo["labels"] == [nucleo.nome, EVENTOS_PUBLICOS_LABEL]
    assert eventos_por_nucleo["series"] == [3, 1]
    assert eventos_por_nucleo["figure"]["data"][0]["type"] == "bar"

    membros_chart = context["membros_chart"]
    assert membros_chart["labels"] == [
        ASSOCIADOS_NUCLEADOS_LABEL,
        ASSOCIADOS_NAO_NUCLEADOS_LABEL,
    ]
    assert membros_chart["series"] == [1, 1]
    assert membros_chart["figure"]["data"][0]["type"] == "pie"


@pytest.mark.django_db
def test_admin_dashboard_forbidden_for_non_admin():
    rf = RequestFactory()
    organizacao = OrganizacaoFactory()
    associado = UserFactory(
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
    )
    request = rf.get(reverse("dashboard:admin_dashboard"))
    request.user = associado

    with pytest.raises(PermissionDenied):
        AdminDashboardView.as_view()(request)
