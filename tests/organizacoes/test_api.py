import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserType
from organizacoes.models import Organizacao, OrganizacaoLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def root_user():
    user = User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="pass",
    )
    return user


def auth(client, user):
    client.force_authenticate(user=user)


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True


@pytest.fixture(autouse=True)
def _no_celery(monkeypatch):
    monkeypatch.setattr("organizacoes.tasks.enviar_email_membros.delay", lambda *a, **k: None)


def test_create_slug_unique(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    data = {
        "nome": "Org",
        "cnpj": faker_ptbr.cnpj(),
        "slug": "org",
    }
    url = reverse("organizacoes_api:organizacao-list")
    resp1 = api_client.post(url, data)
    assert resp1.status_code == status.HTTP_201_CREATED
    resp2 = api_client.post(url, {**data, "cnpj": faker_ptbr.cnpj()})
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST


def test_inativar_reativar(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="o")
    url_inativar = reverse("organizacoes_api:organizacao-inativar", args=[org.pk])
    resp = api_client.patch(url_inativar)
    assert resp.status_code == status.HTTP_200_OK
    org.refresh_from_db()
    assert org.inativa is True and org.inativada_em
    url_reativar = reverse("organizacoes_api:organizacao-reativar", args=[org.pk])
    resp = api_client.patch(url_reativar)
    assert resp.status_code == status.HTTP_200_OK
    org.refresh_from_db()
    assert org.inativa is False and org.inativada_em is None
    assert OrganizacaoLog.objects.filter(organizacao=org, acao="inactivated").exists()


def test_list_excludes_deleted(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org1 = Organizacao.objects.create(nome="A", cnpj=faker_ptbr.cnpj(), slug="a")
    org2 = Organizacao.objects.create(nome="B", cnpj=faker_ptbr.cnpj(), slug="b", deleted=True)
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(url)
    ids = [o["id"] for o in resp.data]
    assert str(org1.id) in ids and str(org2.id) not in ids


def test_logs_access_restricted(api_client, root_user, faker_ptbr):
    other_user = User.objects.create_user(
        username="x",
        email="x@example.com",
        password="pass",
        user_type=UserType.ADMIN,
    )
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="l")
    OrganizacaoLog.objects.create(organizacao=org, acao="created", dados_anteriores={}, dados_novos={})
    url = reverse("organizacoes_api:organizacao-logs", args=[org.pk])
    # unauthorized
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    # non-root denied
    auth(api_client, other_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    auth(api_client, root_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 1
