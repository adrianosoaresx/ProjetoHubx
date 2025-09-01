import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import MagicMock

from accounts.models import User
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


def test_notifica_criacao(api_client, root_user, faker_ptbr, monkeypatch):
    auth(api_client, root_user)
    delay = MagicMock()
    from organizacoes import tasks
    monkeypatch.setattr(tasks.enviar_email_membros, "delay", delay)
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.post(url, {"nome": "Org", "cnpj": faker_ptbr.cnpj()})
    assert resp.status_code == status.HTTP_201_CREATED
    org_id = uuid.UUID(resp.data["id"])
    delay.assert_called_once_with(org_id, "created")


def test_notifica_atualizacao(api_client, root_user, faker_ptbr, monkeypatch):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="upd")
    delay = MagicMock()
    from organizacoes import tasks
    monkeypatch.setattr(tasks.enviar_email_membros, "delay", delay)
    url = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    resp = api_client.patch(url, {"nome": "Nova"}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    delay.assert_called_once_with(org.pk, "updated")


def test_notifica_inativacao(api_client, root_user, faker_ptbr, monkeypatch):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="inact")
    delay = MagicMock()
    from organizacoes import tasks
    monkeypatch.setattr(tasks.enviar_email_membros, "delay", delay)
    url = reverse("organizacoes_api:organizacao-inativar", args=[org.pk])
    resp = api_client.patch(url)
    assert resp.status_code == status.HTTP_200_OK
    delay.assert_called_once_with(org.pk, "inactivated")


def test_notifica_exclusao(api_client, root_user, faker_ptbr, monkeypatch):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="del")
    delay = MagicMock()
    from organizacoes import tasks
    monkeypatch.setattr(tasks.enviar_email_membros, "delay", delay)
    url = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    delay.assert_called_once_with(org.pk, "deleted")
