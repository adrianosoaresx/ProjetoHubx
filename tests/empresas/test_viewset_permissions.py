import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from validate_docbr import CNPJ
from django.contrib.auth import get_user_model

from accounts.models import UserType
from empresas.models import Empresa
from organizacoes.factories import OrganizacaoFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def _criar_empresa(usuario, organizacao, nome="Empresa"):
    return Empresa.objects.create(
        usuario=usuario,
        organizacao=organizacao,
        nome=nome,
        cnpj=CNPJ().generate(),
        tipo="mei",
        municipio="X",
        estado="SC",
    )


def test_admin_filtra_por_organizacao(api_client, admin_user, gerente_user, nucleado_user):
    org2 = OrganizacaoFactory()
    User = get_user_model()
    outro_admin = User.objects.create_user(
        email="other@example.com",
        username="other",
        password="pass",
        user_type=UserType.ADMIN,
        organizacao=org2,
    )
    emp1 = _criar_empresa(admin_user, admin_user.organizacao, "A")
    emp2 = _criar_empresa(gerente_user, admin_user.organizacao, "B")
    emp3 = _criar_empresa(nucleado_user, admin_user.organizacao, "C")
    _criar_empresa(outro_admin, org2, "D")
    url = reverse("empresas_api:empresa-list")
    api_client.force_authenticate(admin_user)
    resp = api_client.get(url)
    ids = {e["id"] for e in resp.data}
    assert ids == {str(emp1.id), str(emp2.id), str(emp3.id)}


@pytest.fixture
def user(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize("user", ["gerente_user", "nucleado_user"], indirect=True)
def test_usuario_filtra_por_proprio_registro(api_client, user, admin_user):
    emp1 = _criar_empresa(user, user.organizacao, "A")
    _criar_empresa(admin_user, user.organizacao, "B")
    url = reverse("empresas_api:empresa-list")
    api_client.force_authenticate(user)
    resp = api_client.get(url)
    ids = {e["id"] for e in resp.data}
    assert ids == {str(emp1.id)}


def test_outros_perfils_sem_acesso(api_client, associado_user, admin_user):
    _criar_empresa(admin_user, admin_user.organizacao, "A")
    url = reverse("empresas_api:empresa-list")
    api_client.force_authenticate(associado_user)
    resp = api_client.get(url)
    assert resp.data == []
