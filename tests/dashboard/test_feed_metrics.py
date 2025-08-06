import pytest
from django.contrib.auth.models import ContentType, Permission
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from dashboard.models import DashboardConfig
from dashboard.services import get_feed_counts, get_top_authors, get_top_tags
from feed.factories import PostFactory
from feed.models import Tag

pytestmark = pytest.mark.django_db


def _grant_perm(user):
    ct = ContentType.objects.get_for_model(DashboardConfig)
    perm, _ = Permission.objects.get_or_create(
        codename="view_metrics", name="Can view metrics", content_type=ct
    )
    user.user_permissions.add(perm)


def test_get_feed_counts(admin_user):
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao, tipo_feed="global")
    data = get_feed_counts(organizacao=admin_user.organizacao_id)
    assert data["total_posts"] == 1
    assert data["posts_by_type"]["global"] == 1


def test_get_top_tags(admin_user):
    tag = Tag.objects.create(nome="django")
    post = PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    post.tags.add(tag)
    tags = get_top_tags(organizacao=admin_user.organizacao_id)
    assert tags[0]["tag"] == "django"
    assert tags[0]["total"] == 1


def test_get_top_authors(admin_user):
    other = UserFactory(organizacao=admin_user.organizacao)
    PostFactory.create_batch(2, autor=admin_user, organizacao=admin_user.organizacao)
    PostFactory(autor=other, organizacao=admin_user.organizacao)
    authors = get_top_authors(organizacao=admin_user.organizacao_id, limite=1)
    assert authors[0]["autor_id"] == admin_user.id


def test_feed_metrics_view(admin_user):
    _grant_perm(admin_user)
    PostFactory(autor=admin_user, organizacao=admin_user.organizacao)
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse("dashboard_api:feed-metrics")
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert "counts" in body and "top_tags" in body

