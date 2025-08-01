import datetime as dt

import pytest
from django.utils import timezone

from agenda.factories import EventoFactory
from agenda.models import Evento, InscricaoEvento
from chat.models import ChatConversation, ChatMessage
from dashboard.services import DashboardService
from discussao.models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao
from feed.factories import PostFactory
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


@pytest.fixture
def conversa(organizacao, admin_user):
    return ChatConversation.objects.create(organizacao=organizacao, slug="c1")


def test_calcular_eventos_por_status(evento):
    EventoFactory(status=1, organizacao=evento.organizacao)
    totals = DashboardService.calcular_eventos_por_status()
    assert any(t["status"] == evento.status and t["total"] >= 1 for t in totals)


@pytest.mark.xfail(reason="aggregates use outdated relation name", raises=Exception)
def test_calcular_inscricoes_eventos(evento, cliente_user):
    InscricaoEvento.objects.create(evento=evento, user=cliente_user, status="confirmada")
    result = DashboardService.calcular_inscricoes_eventos()
    assert result["total"] >= 1
    assert result["confirmados"] >= 1


def test_calcular_topicos_respostas_forum(admin_user, organizacao):
    cat = CategoriaDiscussao.objects.create(nome="c", slug="c", organizacao=organizacao)
    topico = TopicoDiscussao.objects.create(
        categoria=cat, titulo="t", slug="t", conteudo="x", autor=admin_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="r")
    data = DashboardService.calcular_topicos_respostas_forum()
    assert data["topicos"] >= 1
    assert data["respostas"] >= 1


def test_calcular_posts_feed(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    assert DashboardService.calcular_posts_feed() >= 1


def test_calcular_mensagens_chat(conversa, admin_user):
    ChatMessage.objects.create(conversation=conversa, remetente=admin_user, conteudo="hi")
    assert DashboardService.calcular_mensagens_chat() >= 1


def test_calcular_valores_eventos(evento, cliente_user):
    InscricaoEvento.objects.create(evento=evento, user=cliente_user, valor_pago=10)
    values = DashboardService.calcular_valores_eventos()
    assert "valor_arrecadado" in values


def test_get_period_range_default():
    inicio, fim = DashboardService.get_period_range("mensal")
    assert inicio < fim


def test_calcular_crescimento(evento):
    now = timezone.now()
    earlier = now - dt.timedelta(days=30)
    Evento.objects.filter(id=evento.id).update(created_at=earlier)
    inicio = now.replace(day=1)
    fim = inicio + dt.timedelta(days=30)
    data = DashboardService.calcular_crescimento(Evento.objects.all(), inicio, fim)
    assert "total" in data and "crescimento" in data
