import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User, UserType
from organizacoes.models import (
    Organizacao,
    OrganizacaoAtividadeLog,
    OrganizacaoChangeLog,
)

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


def test_create_slug_auto_increment(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    url = reverse("organizacoes_api:organizacao-list")
    data = {"nome": "Org", "cnpj": faker_ptbr.cnpj()}
    resp1 = api_client.post(url, data)
    assert resp1.status_code == status.HTTP_201_CREATED
    resp2 = api_client.post(url, {"nome": "Org", "cnpj": faker_ptbr.cnpj()})
    assert resp2.status_code == status.HTTP_201_CREATED
    assert resp2.data["slug"] == "org-2"


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

    assert org.deleted is False and org.deleted_at is None
    assert OrganizacaoAtividadeLog.all_objects.filter(organizacao=org, acao="inactivated").exists()


def test_patch_inativa_e_rate_limit(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="p")
    url = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    resp = api_client.patch(
        url,
        {"inativa": True, "rate_limit_multiplier": 2},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    org.refresh_from_db()
    assert org.inativa is True and org.inativada_em
    assert org.rate_limit_multiplier == 2
    resp = api_client.patch(url, {"inativa": False}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    org.refresh_from_db()
    assert org.inativa is False and org.inativada_em is None


def test_rate_limit_validation(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="r")
    url = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    resp = api_client.patch(url, {"rate_limit_multiplier": -1}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_excludes_inativa(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org1 = Organizacao.objects.create(nome="A", cnpj=faker_ptbr.cnpj(), slug="a")
    org2 = Organizacao.objects.create(nome="B", cnpj=faker_ptbr.cnpj(), slug="b", inativa=True)
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(url)
    ids = [o["id"] for o in resp.data]
    assert str(org1.id) in ids and str(org2.id) not in ids


def test_list_filter_inativa_tokens(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    active = Organizacao.objects.create(nome="A", cnpj=faker_ptbr.cnpj(), slug="aa")
    inactive = Organizacao.objects.create(
        nome="B", cnpj=faker_ptbr.cnpj(), slug="bb", inativa=True
    )
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(url + "?inativa=yes")
    ids = [o["id"] for o in resp.data]
    assert str(inactive.id) in ids and str(active.id) not in ids
    resp = api_client.get(url + "?inativa=no")
    ids = [o["id"] for o in resp.data]
    assert str(active.id) in ids and str(inactive.id) not in ids


def test_list_permissions(api_client, faker_ptbr, root_user):
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="org")
    user_common = User.objects.create_user(
        username="u",
        email="u@example.com",
        password="pass",
    )
    admin_user = User.objects.create_user(
        username="a",
        email="a@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=org,
    )
    url = reverse("organizacoes_api:organizacao-list")
    auth(api_client, user_common)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    auth(api_client, admin_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK and len(resp.data) == 1
    auth(api_client, root_user)
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK


def test_history_requires_root(api_client, root_user, faker_ptbr):
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="l")
    admin_user = User.objects.create_user(
        username="adm",
        email="adm@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=org,
    )
    OrganizacaoAtividadeLog.objects.create(organizacao=org, acao="created")
    url = reverse("organizacoes_api:organizacao-history", args=[org.pk])
    auth(api_client, admin_user)
    assert api_client.get(url).status_code == status.HTTP_403_FORBIDDEN
    auth(api_client, root_user)
    assert api_client.get(url).status_code == status.HTTP_200_OK


def test_change_log_created_on_update(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="c")
    url = reverse("organizacoes_api:organizacao-detail", args=[org.pk])
    resp = api_client.patch(url, {"nome": "Nova"}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert OrganizacaoChangeLog.all_objects.filter(organizacao=org, campo_alterado="nome").exists()


def test_search_and_ordering(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    o1 = Organizacao.objects.create(nome="B", cnpj=faker_ptbr.cnpj(), slug="b", cidade="X")
    o2 = Organizacao.objects.create(nome="A", cnpj=faker_ptbr.cnpj(), slug="a", cidade="Y")
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(url + "?search=a")
    ids = [o["id"] for o in resp.data]
    assert str(o2.id) in ids and str(o1.id) not in ids
    resp = api_client.get(url + "?ordering=cidade")
    assert [r["id"] for r in resp.data] == [str(o1.id), str(o2.id)]


def test_filter_tipo_cidade_estado(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    o1 = Organizacao.objects.create(
        nome="Org1",
        cnpj=faker_ptbr.cnpj(),
        slug="org1",
        tipo="ong",
        cidade="Cidade1",
        estado="SP",
    )
    o2 = Organizacao.objects.create(
        nome="Org2",
        cnpj=faker_ptbr.cnpj(),
        slug="org2",
        tipo="empresa",
        cidade="Cidade2",
        estado="RJ",
    )
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(url + "?tipo=ong")
    ids = [o["id"] for o in resp.data]
    assert str(o1.id) in ids and str(o2.id) not in ids
    resp = api_client.get(url + "?cidade=Cidade2")
    ids = [o["id"] for o in resp.data]
    assert str(o2.id) in ids and str(o1.id) not in ids
    resp = api_client.get(url + "?estado=SP")
    ids = [o["id"] for o in resp.data]
    assert str(o1.id) in ids and str(o2.id) not in ids


def test_combined_filters(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    o1 = Organizacao.objects.create(
        nome="Org1",
        cnpj=faker_ptbr.cnpj(),
        slug="org1",
        tipo="ong",
        cidade="Cidade1",
        estado="SP",
    )
    o2 = Organizacao.objects.create(
        nome="Org2",
        cnpj=faker_ptbr.cnpj(),
        slug="org2",
        tipo="ong",
        cidade="Cidade1",
        estado="SP",
        inativa=True,
    )
    Organizacao.objects.create(
        nome="Org3",
        cnpj=faker_ptbr.cnpj(),
        slug="org3",
        tipo="empresa",
        cidade="Cidade2",
        estado="RJ",
    )
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.get(
        url
        + "?search=org2&tipo=ong&cidade=Cidade1&estado=SP&inativa=yes"
    )
    ids = [o["id"] for o in resp.data]
    assert ids == [str(o2.id)]
    resp = api_client.get(
        url + "?search=org1&tipo=ong&cidade=Cidade1&estado=SP"
    )
    ids = [o["id"] for o in resp.data]
    assert ids == [str(o1.id)]


def test_invalid_cnpj_api(api_client, root_user):
    auth(api_client, root_user)
    url = reverse("organizacoes_api:organizacao-list")
    resp = api_client.post(url, {"nome": "Org", "cnpj": "123"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_history_export_csv(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = Organizacao.objects.create(nome="Org", cnpj=faker_ptbr.cnpj(), slug="csv")
    OrganizacaoAtividadeLog.objects.create(organizacao=org, acao="created")
    url = reverse("organizacoes_api:organizacao-history", args=[org.pk]) + "?export=csv"
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"] == "text/csv"
