import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
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


def create_org(faker):
    return Organizacao.objects.create(
        nome="Org",
        cnpj=faker.cnpj(),
        slug="org",
    )



@pytest.mark.parametrize(
    "model, kwargs, field",
    [
        (
            OrganizacaoChangeLog,
            {
                "campo_alterado": "nome",
                "valor_antigo": "Org",
                "valor_novo": "Nova",
            },
            "valor_novo",
        ),
        (OrganizacaoAtividadeLog, {"acao": "created"}, "acao"),
    ],
)
def test_logs_are_immutable(model, kwargs, field, faker_ptbr):
    org = create_org(faker_ptbr)
    log = model.objects.create(organizacao=org, **kwargs)
    with pytest.raises(RuntimeError):
        setattr(log, field, "changed")
        log.save()
    with pytest.raises(RuntimeError):
        log.delete()
