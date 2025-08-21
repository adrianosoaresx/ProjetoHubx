import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from agenda.factories import EventoFactory
from nucleos.factories import NucleoFactory
from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


@pytest.fixture
def organizacao():
    return OrganizacaoFactory()


@pytest.fixture
def nucleo(organizacao):
    return NucleoFactory(organizacao=organizacao)


@pytest.fixture
def root_user():
    return User.objects.create_user(
        username="root",
        email="root@example.com",
        password="pass",
        user_type=UserType.ROOT,
    )


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
    )


@pytest.fixture
def cliente_user(organizacao):
    return User.objects.create_user(
        username="cliente",
        email="cliente@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleado_user(organizacao, nucleo):
    return User.objects.create_user(
        username="nucleado",
        email="nucleado@example.com",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
        nucleo=nucleo,
    )


@pytest.fixture
def convidado_user(organizacao):
    return User.objects.create_user(
        username="convidado",
        email="convidado@example.com",
        password="pass",
        user_type=UserType.CONVIDADO,
        organizacao=organizacao,
    )


@pytest.fixture
def evento(admin_user, organizacao):
    return EventoFactory(organizacao=organizacao, coordenador=admin_user)
