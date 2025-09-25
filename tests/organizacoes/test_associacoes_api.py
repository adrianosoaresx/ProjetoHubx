import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from feed.models import FeedPluginConfig
from organizacoes.models import Organizacao


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root_user():
    return User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="pass",
    )


def auth(client, user):
    client.force_authenticate(user=user)


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


def test_crud_plugin(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="org")
    url = reverse("organizacoes_api:organizacao-plugins-list", args=[org.pk])
    data = {"module_path": "feed.tests.sample_plugin.DummyPlugin", "frequency": 1}
    resp = api_client.post(url, data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    plugin_id = resp.data["id"]
    assert FeedPluginConfig.objects.filter(pk=plugin_id, organizacao=org).exists()

    detail = reverse("organizacoes_api:organizacao-plugins-detail", args=[org.pk, plugin_id])
    resp = api_client.patch(detail, {"frequency": 2}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert FeedPluginConfig.objects.get(pk=plugin_id).frequency == 2

    resp = api_client.delete(detail)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not FeedPluginConfig.objects.filter(pk=plugin_id).exists()
