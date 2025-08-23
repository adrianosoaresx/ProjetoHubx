import os

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from empresas.models import Tag
from organizacoes.factories import OrganizacaoFactory

User = get_user_model()


@pytest.fixture
def organizacao(db):
    return OrganizacaoFactory()


@pytest.fixture
def admin_user(db, organizacao):
    return User.objects.create_user(
        email="admin@example.com",
        username="admin",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=organizacao,
    )


@pytest.fixture
def gerente_user(db, organizacao):
    return User.objects.create_user(
        email="gerente@example.com",
        username="gerente",
        password="pass",
        user_type=UserType.COORDENADOR,
        organizacao=organizacao,
    )


@pytest.fixture
def associado_user(db, organizacao):
    return User.objects.create_user(
        email="assoc@example.com",
        username="assoc",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


@pytest.fixture
def nucleado_user(db, organizacao):
    return User.objects.create_user(
        email="nucleado@example.com",
        username="nucleado",
        password="pass",
        user_type=UserType.NUCLEADO,
        organizacao=organizacao,
    )


@pytest.fixture
def root_user(db):
    return User.objects.create_superuser(
        email="root@example.com",
        username="root",
        password="pass",
    )


@pytest.fixture
def tag_factory(db):
    def factory(**kwargs):
        return Tag.objects.create(**kwargs)

    return factory




@pytest.fixture(autouse=True)
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    yield
    for root, dirs, files in os.walk(tmp_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
