import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from financeiro.models import FinanceiroLog, FinanceiroTaskLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def auth(client: APIClient, user):
    client.force_authenticate(user=user)


def test_logs_permission(client):
    url = reverse("financeiro_api:log-list")
    resp = client.get(url)
    assert resp.status_code in {401, 403}
    user = UserFactory(user_type=UserType.ASSOCIADO)
    auth(client, user)
    resp = client.get(url)
    assert resp.status_code == 403
    admin = UserFactory(user_type=UserType.ADMIN)
    auth(client, admin)
    FinanceiroLog.objects.create(
        usuario=admin,
        acao=FinanceiroLog.Acao.IMPORTAR,
        dados_anteriores={},
        dados_novos={},
    )
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.data["count"] == 1


def test_task_logs_filter(client):
    admin = UserFactory(user_type=UserType.ADMIN)
    auth(client, admin)
    FinanceiroTaskLog.objects.create(nome_tarefa="t1", status="ok")
    FinanceiroTaskLog.objects.create(nome_tarefa="t2", status="erro")
    url = reverse("financeiro_api:task-log-list")
    resp = client.get(url, {"status": "erro"})
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["nome_tarefa"] == "t2"
