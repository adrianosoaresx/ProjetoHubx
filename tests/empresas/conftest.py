import os

import pytest
from django.contrib.auth import get_user_model

from accounts.models import UserType
from empresas.factories import EmpresaFactory
from empresas.models import ContatoEmpresa
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
def empresa(db, gerente_user):
    return EmpresaFactory(usuario=gerente_user, organizacao=gerente_user.organizacao)


@pytest.fixture
def outra_empresa(db, gerente_user):
    return EmpresaFactory(usuario=gerente_user, organizacao=gerente_user.organizacao)


@pytest.fixture
def contato_principal(db, empresa):
    return ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Fulano",
        cargo="CEO",
        email="contato1@example.com",
        telefone="1111",
        principal=True,
    )


@pytest.fixture
def contato_secundario(db, empresa):
    return ContatoEmpresa.objects.create(
        empresa=empresa,
        nome="Beltrano",
        cargo="CTO",
        email="contato2@example.com",
        telefone="2222",
        principal=False,
    )


@pytest.fixture(autouse=True)
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    yield
    for root, dirs, files in os.walk(tmp_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
