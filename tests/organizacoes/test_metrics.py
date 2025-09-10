import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from organizacoes.factories import OrganizacaoFactory
from organizacoes import metrics as m

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root_user():
    return User.objects.create_superuser(username="root", email="root@example.com", password="pass")


def auth(client, user):
    client.force_authenticate(user=user)


def test_api_latency_metrics_recorded(api_client, root_user):
    m.list_latency_seconds.clear()
    m.detail_latency_seconds.clear()
    auth(api_client, root_user)
    org = OrganizacaoFactory()
    url_list = reverse("organizacoes_api:organizacao-list")
    api_client.get(url_list)
    url_detail = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    api_client.get(url_detail)
    assert m.list_latency_seconds._sum.get() > 0
    assert m.detail_latency_seconds._sum.get() > 0


@pytest.mark.parametrize("hist", [m.list_latency_seconds, m.detail_latency_seconds])
def test_histograms_bucket_250ms(hist):
    hist.clear()
    hist.observe(0.2)
    sample = hist.collect()[0]
    buckets = {float(s.labels["le"]): s.value for s in sample.samples if s.name.endswith("_bucket")}
    assert buckets[0.25] >= 1
