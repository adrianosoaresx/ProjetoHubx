import pytest
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from eventos.models import Tarefa, TarefaLog


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def _admin_user(organizacao):
    return UserFactory(
        organizacao=organizacao,
        user_type=UserType.ADMIN,
        is_superuser=True,
        is_staff=True,
        nucleo_obj=None,
    )


def _tarefa_data():
    now = timezone.now()
    return {
        "titulo": "T",
        "descricao": "d",
        "data_inicio": now.isoformat(),
        "data_fim": (now + timezone.timedelta(hours=1)).isoformat(),
    }


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_tarefa_logs(api_client: APIClient) -> None:
    org = OrganizacaoFactory()
    user = _admin_user(org)
    api_client.force_authenticate(user)

    url = reverse("eventos_api:tarefa-list")
    resp = api_client.post(url, _tarefa_data(), format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    tarefa_id = resp.data["id"]
    assert TarefaLog.objects.filter(tarefa_id=tarefa_id, acao="tarefa_criada", usuario=user).exists()

    url_detail = reverse("eventos_api:tarefa-detail", args=[tarefa_id])
    resp = api_client.patch(url_detail, {"descricao": "nova"}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert TarefaLog.objects.filter(tarefa_id=tarefa_id, acao="tarefa_atualizada").exists()

    url_concluir = reverse("eventos_api:tarefa-concluir", args=[tarefa_id])
    resp = api_client.post(url_concluir)
    assert resp.status_code == status.HTTP_200_OK
    assert TarefaLog.objects.filter(tarefa_id=tarefa_id, acao="tarefa_concluida").exists()

    api_client.delete(url_detail)
    assert TarefaLog.objects.filter(tarefa_id=tarefa_id, acao="tarefa_excluida").exists()
