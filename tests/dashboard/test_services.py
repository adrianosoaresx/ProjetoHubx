import datetime as dt

import pytest
from django.utils import timezone

from accounts.models import User, UserType
from agenda.factories import EventoFactory
from agenda.models import Evento, InscricaoEvento
from chat.models import ChatChannel, ChatMessage
from dashboard.services import DashboardMetricsService, DashboardService
from discussao.models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao
from feed.factories import PostFactory
from organizacoes.factories import OrganizacaoFactory
from financeiro.models import CentroCusto, LancamentoFinanceiro

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


@pytest.fixture
def conversa(organizacao, admin_user):
    return ChatChannel.objects.create(titulo="c1", contexto_tipo="organizacao", contexto_id=organizacao.id)


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
    ChatMessage.objects.create(channel=conversa, remetente=admin_user, conteudo="hi")
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
    Evento.objects.filter(id=evento.id).update(created=earlier)
    inicio = now.replace(day=1)
    fim = inicio + dt.timedelta(days=30)
    data = DashboardService.calcular_crescimento(Evento.objects.all(), inicio, fim)
    assert "total" in data and "crescimento" in data


def test_get_metrics_with_filters(admin_user, organizacao):
    other_org = OrganizacaoFactory()
    User.objects.create_user(
        email="other@example.com",
        username="other",
        password="x",
        user_type=UserType.ADMIN,
        organizacao=other_org,
    )
    metrics = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=admin_user.organizacao_id,
        metricas=["num_users"],
    )
    assert set(metrics.keys()) == {"num_users"}
    assert metrics["num_users"]["total"] >= 1


def test_get_metrics_cache_differentiates(admin_user):
    other_org = OrganizacaoFactory()
    User.objects.create_user(
        email="another@example.com",
        username="another",
        password="x",
        user_type=UserType.ADMIN,
        organizacao=other_org,
    )
    metrics1 = DashboardMetricsService.get_metrics(
        admin_user, escopo="organizacao", organizacao_id=admin_user.organizacao_id
    )
    metrics2 = DashboardMetricsService.get_metrics(admin_user, escopo="global")
    assert metrics1["num_users"]["total"] < metrics2["num_users"]["total"]


def test_get_metrics_cache_shared_between_users(admin_user, django_assert_num_queries):
    other = User.objects.create_user(
        email="same@example.com",
        username="same",
        password="x",
        user_type=UserType.ADMIN,
        organizacao=admin_user.organizacao,
    )
    DashboardMetricsService.get_metrics(admin_user, escopo="organizacao", organizacao_id=admin_user.organizacao_id)
    with django_assert_num_queries(0):
        DashboardMetricsService.get_metrics(other, escopo="organizacao", organizacao_id=admin_user.organizacao_id)


def test_get_metrics_permission_denied(cliente_user, admin_user):
    with pytest.raises(PermissionError):
        DashboardMetricsService.get_metrics(
            cliente_user, escopo="organizacao", organizacao_id=admin_user.organizacao_id
        )


def test_get_metrics_invalid_period(admin_user):
    with pytest.raises(ValueError):
        DashboardMetricsService.get_metrics(admin_user, periodo="xxx")


def test_get_metrics_invalid_date(admin_user):
    with pytest.raises(ValueError):
        DashboardMetricsService.get_metrics(admin_user, inicio="bad-date")


def test_get_metrics_inscricoes_confirmadas(admin_user, evento, cliente_user):
    InscricaoEvento.objects.create(evento=evento, user=cliente_user, status="confirmada")
    metrics = DashboardMetricsService.get_metrics(
        admin_user, metricas=["inscricoes_confirmadas"], escopo="organizacao", organizacao_id=evento.organizacao_id
    )
    assert metrics["inscricoes_confirmadas"]["total"] >= 1


def test_get_metrics_lancamentos_pendentes(admin_user, organizacao):
    centro = CentroCusto.objects.create(nome="c", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=organizacao)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        valor=10,
    )
    metrics = DashboardMetricsService.get_metrics(
        admin_user, metricas=["lancamentos_pendentes"], escopo="organizacao", organizacao_id=organizacao.id
    )
    assert metrics["lancamentos_pendentes"]["total"] >= 1
