import pytest
from django.urls import reverse
from django.utils.text import slugify

from accounts.models import User, UserType
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def faker_ptbr():
    from faker import Faker

    return Faker("pt_BR")


@pytest.fixture
def superadmin_user(client):
    user = User.objects.create_user(
        username="root",
        email="root@example.com",
        password="pass",
        user_type=UserType.ROOT,
    )
    client.force_login(user)
    return client


@pytest.fixture
def admin_user(client):
    user = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
    )
    client.force_login(user)
    return client


@pytest.fixture
def organizacao(faker_ptbr):
    name = faker_ptbr.company()
    return Organizacao.objects.create(nome=name, cnpj=faker_ptbr.cnpj(), slug=slugify(name))


def test_list_view_superadmin(superadmin_user, organizacao):
    url = reverse("organizacoes:list")
    response = superadmin_user.get(url)
    assert response.status_code == 200
    assert set(response.context["object_list"]) == set(Organizacao.objects.all())


def test_list_view_denied_for_non_superadmin(admin_user):
    url = reverse("organizacoes:list")
    response = admin_user.get(url)
    assert response.status_code == 403


def test_create_view_superadmin(superadmin_user, faker_ptbr):
    url = reverse("organizacoes:create")
    data = {"nome": "Nova Org", "cnpj": faker_ptbr.cnpj(), "slug": "nova-org"}
    response = superadmin_user.post(url, data=data, follow=True)
    assert response.status_code == 200
    assert Organizacao.objects.filter(nome="Nova Org").exists()
    msgs = list(response.context["messages"])
    assert any("criada" in m.message.lower() for m in msgs)


def test_create_view_denied_for_admin(admin_user, faker_ptbr):
    url = reverse("organizacoes:create")
    data = {"nome": "Org X", "cnpj": faker_ptbr.cnpj(), "slug": "org-x"}
    response = admin_user.post(url, data=data)
    assert response.status_code == 403
    assert not Organizacao.objects.filter(nome="Org X").exists()


def test_update_view_superadmin(superadmin_user, organizacao):
    url = reverse("organizacoes:update", args=[organizacao.pk])
    response = superadmin_user.post(
        url,
        {"nome": "Editada", "cnpj": organizacao.cnpj, "slug": "editada"},
        follow=True,
    )
    assert response.status_code == 200
    organizacao.refresh_from_db()
    assert organizacao.nome == "Editada"
    msgs = list(response.context["messages"])
    assert any("atualizada" in m.message.lower() for m in msgs)


def test_update_view_denied_for_admin(admin_user, organizacao):
    url = reverse("organizacoes:update", args=[organizacao.pk])
    response = admin_user.post(url, {"nome": "X", "cnpj": organizacao.cnpj, "slug": "x"})
    assert response.status_code == 403
    organizacao.refresh_from_db()
    assert organizacao.nome != "X"


def test_delete_view_superadmin(superadmin_user, organizacao):
    url = reverse("organizacoes:delete", args=[organizacao.pk])
    response = superadmin_user.post(url, follow=True)
    assert response.status_code == 200
    assert not Organizacao.objects.filter(pk=organizacao.pk).exists()


def test_delete_view_denied_for_admin(admin_user, organizacao):
    url = reverse("organizacoes:delete", args=[organizacao.pk])
    response = admin_user.post(url)
    assert response.status_code == 403
    assert Organizacao.objects.filter(pk=organizacao.pk).exists()
