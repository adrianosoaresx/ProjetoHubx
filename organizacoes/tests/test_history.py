import csv
from io import StringIO

import pytest
from django.urls import reverse
from rest_framework import status
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


def test_history_export_csv(api_client, root_user, faker_ptbr):
    auth(api_client, root_user)
    org = create_org(faker_ptbr)
    OrganizacaoChangeLog.objects.create(
        organizacao=org,
        campo_alterado="nome",
        valor_antigo="Org",
        valor_novo="Nova",
        alterado_por=root_user,
    )
    OrganizacaoAtividadeLog.objects.create(
        organizacao=org,
        acao="created",
        usuario=root_user,
    )
    url = reverse("organizacoes_api:organizacao-history", args=[org.pk]) + "?export=csv"
    resp = api_client.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"] == "text/csv"
    assert resp["Content-Disposition"].startswith(
        f'attachment; filename="organizacao_{org.pk}_logs.csv"'
    )
    rows = list(csv.reader(StringIO(resp.content.decode("utf-8"))))
    assert rows[0] == [
        "tipo",
        "campo/acao",
        "valor_antigo",
        "valor_novo",
        "usuario",
        "data",
    ]
    assert any(
        r[0] == "change"
        and r[1] == "nome"
        and r[2] == "Org"
        and r[3] == "Nova"
        and r[4] == root_user.email
        for r in rows[1:]
    )
    assert any(
        r[0] == "activity"
        and r[1] == "created"
        and r[4] == root_user.email
        for r in rows[1:]
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
