import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import UserType
from organizacoes.models import Organizacao

pytestmark = pytest.mark.django_db


def create_user(email: str, username: str, user_type: UserType, **extra):
    User = get_user_model()
    return User.objects.create_user(
        email=email,
        username=username,
        password="pwd",
        user_type=user_type,
        **extra,
    )


def test_admin_list_associados(client):
    admin = create_user("admin@example.com", "admin", UserType.ADMIN)
    assoc = create_user(
        "assoc@example.com",
        "assoc",
        UserType.ASSOCIADO,
        is_associado=True,
    )
    client.force_login(admin)
    resp = client.get(reverse("accounts:associados_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()


def test_search_associados(client):
    admin = create_user("a2@example.com", "a2", UserType.ADMIN)
    create_user("john@example.com", "john", UserType.ASSOCIADO, is_associado=True)
    create_user("jane@example.com", "jane", UserType.ASSOCIADO, is_associado=True)
    client.force_login(admin)
    resp = client.get(reverse("accounts:associados_lista"), {"q": "john"})
    content = resp.content.decode()
    assert "john" in content
    assert "jane" not in content


def test_coordenador_list_associados(client):
    org = Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")
    coord = create_user(
        "coord@example.com",
        "coord",
        UserType.COORDENADOR,
        organizacao=org,
    )
    assoc = create_user(
        "assoc2@example.com",
        "assoc2",
        UserType.ASSOCIADO,
        is_associado=True,
        organizacao=org,
    )
    client.force_login(coord)
    resp = client.get(reverse("accounts:associados_lista"))
    assert resp.status_code == 200
    assert assoc.username in resp.content.decode()
