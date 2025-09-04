import datetime as dt

import pytest

from django.core.cache import cache

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from accounts.models import User, UserType
from agenda.factories import EventoFactory
from eventos.models import Evento, InscricaoEvento
from dashboard.services import DashboardMetricsService, DashboardService
from discussao.models import CategoriaDiscussao, RespostaDiscussao, TopicoDiscussao
from feed.factories import PostFactory
from feed.models import Post
from financeiro.models import CentroCusto, LancamentoFinanceiro
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


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


def test_calcular_posts_feed_filters(admin_user, organizacao):
    other_org = OrganizacaoFactory()
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    PostFactory(autor=admin_user, organizacao=other_org)
    assert DashboardService.calcular_posts_feed(organizacao_id=admin_user.organizacao_id) == 1


def test_calcular_posts_feed_24h(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    old = PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    Post.objects.filter(id=old.id).update(created_at=timezone.now() - dt.timedelta(days=2))
    assert DashboardService.calcular_posts_feed_24h() == 1


def test_calcular_topicos_respostas_discussao(admin_user, organizacao):
    other_org = OrganizacaoFactory()
    cat1 = CategoriaDiscussao.objects.create(nome="c", slug="c", organizacao=organizacao)
    cat2 = CategoriaDiscussao.objects.create(nome="c2", slug="c2", organizacao=other_org)
    topico1 = TopicoDiscussao.objects.create(
        categoria=cat1, titulo="t", slug="t", conteudo="x", autor=admin_user, publico_alvo=0
    )
    TopicoDiscussao.objects.create(
        categoria=cat2, titulo="t2", slug="t2", conteudo="x", autor=admin_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico1, autor=admin_user, conteudo="r")
    assert DashboardService.calcular_topicos_discussao(organizacao_id=organizacao.id) == 1
    assert DashboardService.calcular_respostas_discussao(organizacao_id=organizacao.id) == 1


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
    data = DashboardService.calcular_crescimento(Evento.objects.all(), inicio, fim, campo="created")
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
    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=admin_user.organizacao_id,
        metricas=["num_users"],
    )
    assert set(metrics.keys()) == {"num_users"}
    assert metrics["num_users"]["total"] >= 1


def test_get_metrics_includes_new_metrics(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    cat = CategoriaDiscussao.objects.create(nome="c", slug="c", organizacao=admin_user.organizacao)
    topico = TopicoDiscussao.objects.create(
        categoria=cat, titulo="t", slug="t", conteudo="x", autor=admin_user, publico_alvo=0
    )
    RespostaDiscussao.objects.create(topico=topico, autor=admin_user, conteudo="r")
    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=admin_user.organizacao_id,
        metricas=[
            "num_posts_feed_total",
            "num_posts_feed_recent",
            "num_topicos",
            "num_respostas",
        ],
    )
    assert metrics["num_posts_feed_total"]["total"] == 1
    assert metrics["num_posts_feed_recent"]["total"] == 1
    assert metrics["num_topicos"]["total"] == 1
    assert metrics["num_respostas"]["total"] == 1


def test_get_metrics_cache_differentiates(admin_user):
    other_org = OrganizacaoFactory()
    User.objects.create_user(
        email="another@example.com",
        username="another",
        password="x",
        user_type=UserType.ADMIN,
        organizacao=other_org,
    )
    metrics1, _ = DashboardMetricsService.get_metrics(
        admin_user, escopo="organizacao", organizacao_id=admin_user.organizacao_id
    )
    metrics2, _ = DashboardMetricsService.get_metrics(admin_user, escopo="global")
    assert metrics1["num_users"]["total"] < metrics2["num_users"]["total"]


def test_get_metrics_cache_not_shared_between_users(admin_user):
    other = User.objects.create_user(
        email="same@example.com",
        username="same",
        password="x",
        user_type=UserType.ADMIN,
        organizacao=admin_user.organizacao,
    )
    cache.clear()
    DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=admin_user.organizacao_id,
        metricas=["num_users"],
    )
    keys_before = len(cache._cache)
    DashboardMetricsService.get_metrics(
        other,
        escopo="organizacao",
        organizacao_id=admin_user.organizacao_id,
        metricas=["num_users"],
    )
    assert len(cache._cache) == keys_before + 1


def test_inscricao_evento_signal_clears_cache_for_user_only(admin_user, cliente_user, evento):
    cache.clear()
    DashboardMetricsService.get_metrics(
        admin_user, escopo="auto", metricas=["num_users"]
    )
    DashboardMetricsService.get_metrics(
        cliente_user, escopo="auto", metricas=["num_users"]
    )
    prefix_admin = f"dashboard-{admin_user.pk}-{admin_user.user_type}-"
    prefix_cliente = f"dashboard-{cliente_user.pk}-{cliente_user.user_type}-"
    assert any(prefix_admin in k for k in cache._cache.keys())
    assert any(prefix_cliente in k for k in cache._cache.keys())
    InscricaoEvento.objects.create(evento=evento, user=admin_user, status="confirmada")
    assert not any(prefix_admin in k for k in cache._cache.keys())
    assert any(prefix_cliente in k for k in cache._cache.keys())


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


def test_get_metrics_invalid_date_order(admin_user):
    inicio = timezone.now()
    fim = inicio - dt.timedelta(days=1)
    with pytest.raises(ValueError):
        DashboardMetricsService.get_metrics(admin_user, inicio=inicio, fim=fim)


def test_get_metrics_inscricoes_confirmadas(admin_user, evento, cliente_user):
    another_user = User.objects.create_user(
        email="other@example.com",
        username="other",
        password="x",
        user_type=UserType.ASSOCIADO,
        organizacao=evento.organizacao,
    )
    prev_user = User.objects.create_user(
        email="prev@example.com",
        username="prev",
        password="x",
        user_type=UserType.ASSOCIADO,
        organizacao=evento.organizacao,
    )

    now = timezone.now()
    prev_month = now - relativedelta(months=1)

    InscricaoEvento.objects.create(
        evento=evento,
        user=cliente_user,
        status="confirmada",
        data_confirmacao=now,
    )
    InscricaoEvento.objects.create(
        evento=evento,
        user=another_user,
        status="confirmada",
        data_confirmacao=now,
    )
    InscricaoEvento.objects.create(
        evento=evento,
        user=prev_user,
        status="confirmada",
        data_confirmacao=prev_month,
    )

    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user,
        metricas=["inscricoes_confirmadas"],
        escopo="organizacao",
        organizacao_id=evento.organizacao_id,
    )
    assert metrics["inscricoes_confirmadas"]["total"] == 2
    assert metrics["inscricoes_confirmadas"]["crescimento"] == pytest.approx(100.0)


def test_get_metrics_lancamentos_pendentes(admin_user, organizacao):
    centro = CentroCusto.objects.create(nome="c", tipo=CentroCusto.Tipo.ORGANIZACAO, organizacao=organizacao)
    LancamentoFinanceiro.objects.create(
        centro_custo=centro,
        tipo=LancamentoFinanceiro.Tipo.APORTE_INTERNO,
        valor=10,
    )
    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user, metricas=["lancamentos_pendentes"], escopo="organizacao", organizacao_id=organizacao.id
    )
    assert metrics["lancamentos_pendentes"]["total"] >= 1
