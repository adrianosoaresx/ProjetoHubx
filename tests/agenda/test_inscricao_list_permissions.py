import pytest
from django.urls import reverse

from accounts.models import User, UserType
from organizacoes.models import Organizacao


pytestmark = pytest.mark.django_db


@pytest.fixture
def organizacao():
    return Organizacao.objects.create(nome="Org", cnpj="00000000000191")


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
def associado_user(organizacao):
    return User.objects.create_user(
        username="associado",
        email="assoc@example.com",
        password="pass",
        user_type=UserType.ASSOCIADO,
        organizacao=organizacao,
    )


def test_inscricao_list_requires_gerente(client, associado_user):
    client.force_login(associado_user)
    resp = client.get(reverse("agenda:inscricao_list"))
    assert resp.status_code == 302


def test_inscricao_list_allows_gerente(client, gerente_user):
    client.force_login(gerente_user)
    resp = client.get(reverse("agenda:inscricao_list"))
    assert resp.status_code == 200

