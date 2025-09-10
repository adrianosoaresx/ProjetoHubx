import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserType
from eventos.models import Tarefa, TarefaLog
from organizacoes.models import Organizacao

pytestmark = pytest.mark.urls("Hubx.urls")


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00.000.000/0001-00", slug="org")


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
def test_criar_tarefa_log(client, admin_user):
    client.force_login(admin_user)
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    resp = client.post(
        reverse("eventos:tarefa_criar"),
        {
            "titulo": "Teste",
            "descricao": "Desc",
            "data_inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": fim.strftime("%Y-%m-%dT%H:%M"),
            "responsavel": admin_user.pk,
            "status": "pendente",
        },
    )
    assert resp.status_code == 302
    tarefa = Tarefa.objects.get(titulo="Teste")
    assert TarefaLog.objects.filter(tarefa=tarefa, acao="tarefa_criada", usuario=admin_user).exists()


@pytest.mark.django_db
def test_atualizar_tarefa_log(client, admin_user):
    inicio = timezone.now()
    fim = inicio + timedelta(hours=1)
    tarefa = Tarefa.objects.create(
        titulo="Old",
        descricao="Desc",
        data_inicio=inicio,
        data_fim=fim,
        responsavel=admin_user,
        organizacao=admin_user.organizacao,
    )
    client.force_login(admin_user)
    resp = client.post(
        reverse("eventos:tarefa_editar", args=[tarefa.pk]),
        {
            "titulo": "New",
            "descricao": "Desc",
            "data_inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
            "data_fim": fim.strftime("%Y-%m-%dT%H:%M"),
            "responsavel": admin_user.pk,
            "status": "pendente",
        },
    )
    assert resp.status_code == 302
    tarefa.refresh_from_db()
    assert tarefa.titulo == "New"
    assert TarefaLog.objects.filter(tarefa=tarefa, acao="tarefa_atualizada", usuario=admin_user).exists()
