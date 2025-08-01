import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from organizacoes.models import Organizacao

User = get_user_model()


@pytest.fixture
def organizacao(db):
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-99", slug="org")


@pytest.fixture
def admin_user(organizacao):
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def gerente_user(organizacao):
    return User.objects.create_user(
        username="gerente",
        email="gerente@example.com",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
        is_coordenador=True,
        is_associado=True,
    )


@pytest.fixture
def associado_user(organizacao):
    return User.objects.create_user(
        username="associado",
        email="associado@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
        is_associado=True,
    )


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def gerente_client(client, gerente_user):
    client.force_login(gerente_user)
    return client


@pytest.fixture
def associado_client(client, associado_user):
    client.force_login(associado_user)
    return client
