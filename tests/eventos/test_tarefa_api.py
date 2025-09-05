from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import UserType
from eventos.models import Tarefa, TarefaLog
from organizacoes.models import Organizacao

pytestmark = pytest.mark.urls("Hubx.urls")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(
        nome="Org", cnpj="00.000.000/0001-00", slug="org"
    )


@pytest.fixture
def admin_user(django_user_model, organizacao):
    return django_user_model.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="password",
        organizacao=organizacao,
        user_type=UserType.ADMIN,
    )


@pytest.mark.django_db
def test_criar_tarefa(api_client: APIClient, admin_user):
    api_client.force_authenticate(admin_user)
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    resp = api_client.post(
        "/api/eventos/tarefas/",
        {
            "titulo": "Teste",
            "descricao": "Desc",
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
        },
    )
    assert resp.status_code == 201
    tarefa = Tarefa.objects.get(id=resp.data["id"])
    assert TarefaLog.objects.filter(
        tarefa=tarefa, acao="tarefa_criada", usuario=admin_user
    ).exists()


@pytest.mark.django_db
def test_concluir_tarefa(api_client: APIClient, admin_user):
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    tarefa = Tarefa.objects.create(
        titulo="T",
        descricao="",
        data_inicio=inicio,
        data_fim=fim,
        responsavel=admin_user,
        organizacao=admin_user.organizacao,
    )
    api_client.force_authenticate(admin_user)
    resp = api_client.post(f"/api/eventos/tarefas/{tarefa.id}/concluir/")
    assert resp.status_code == 200
    tarefa.refresh_from_db()
    assert tarefa.status == "concluida"
    assert TarefaLog.objects.filter(
        tarefa=tarefa, acao="tarefa_concluida", usuario=admin_user
    ).exists()


@pytest.mark.django_db
def test_excluir_tarefa(api_client: APIClient, admin_user):
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    tarefa = Tarefa.objects.create(
        titulo="T",
        descricao="",
        data_inicio=inicio,
        data_fim=fim,
        responsavel=admin_user,
        organizacao=admin_user.organizacao,
    )
    api_client.force_authenticate(admin_user)
    resp = api_client.delete(f"/api/eventos/tarefas/{tarefa.id}/")
    assert resp.status_code == 204
    tarefa.refresh_from_db()
    assert tarefa.deleted is True
    assert TarefaLog.objects.filter(
        tarefa=tarefa, acao="tarefa_excluida", usuario=admin_user
    ).exists()

