from datetime import timedelta

import pytest
from django.utils import timezone

from dashboard.services import DashboardMetricsService
from feed.models import Post, PostView, Reacao
from organizacoes.factories import OrganizacaoFactory
from tokens.models import TokenAcesso, TokenUsoLog

pytestmark = pytest.mark.django_db


def test_feed_engagement_metrics(admin_user, organizacao):
    post = Post.objects.create(
        autor=admin_user,
        organizacao=organizacao,
        tipo_feed="global",
        conteudo="x",
    )
    Reacao.objects.create(post=post, user=admin_user, vote="like")
    Reacao.objects.create(post=post, user=admin_user, vote="share")
    opened = timezone.now() - timedelta(minutes=5)
    PostView.objects.create(post=post, user=admin_user, opened_at=opened, closed_at=timezone.now())

    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=organizacao.id,
        metricas=[
            "total_curtidas",
            "total_compartilhamentos",
            "tempo_medio_leitura",
            "posts_populares_24h",
        ],
    )
    assert metrics["total_curtidas"]["total"] == 1
    assert metrics["total_compartilhamentos"]["total"] == 1
    assert metrics["tempo_medio_leitura"]["total"] >= 300
    assert metrics["posts_populares_24h"]["total"][0]["post_id"] == str(post.id)


def test_token_metrics_filtering(admin_user, organizacao):
    token1 = TokenAcesso.objects.create(
        gerado_por=admin_user,
        organizacao=organizacao,
        tipo_destino="admin",
    )
    TokenUsoLog.objects.create(token=token1, acao=TokenUsoLog.Acao.USO)

    outra_org = OrganizacaoFactory()
    token2 = TokenAcesso.objects.create(
        gerado_por=admin_user,
        organizacao=outra_org,
        tipo_destino="admin",
    )
    TokenUsoLog.objects.create(token=token2, acao=TokenUsoLog.Acao.USO)

    metrics, _ = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=organizacao.id,
        metricas=["tokens_gerados", "tokens_consumidos"],
    )
    assert metrics["tokens_gerados"]["total"] == 1
    assert metrics["tokens_consumidos"]["total"] == 1

    metrics_filtered, _ = DashboardMetricsService.get_metrics(
        admin_user,
        escopo="organizacao",
        organizacao_id=organizacao.id,
        metricas=["tokens_gerados"],
    )
    assert "tokens_gerados" in metrics_filtered
    assert "tokens_consumidos" not in metrics_filtered
