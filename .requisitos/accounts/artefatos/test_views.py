import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import ConfiguracaoConta

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(user_factory):
    user = user_factory(password="Senha123!")
    configuracao = ConfiguracaoConta.objects.create(user=user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def test_ver_perfil(client):
    api, user = client
    url = reverse("perfil-usuario")
    resp = api.get(url)
    assert resp.status_code == 200
    assert resp.data["email"] == user.email


def test_editar_perfil(client):
    api, _ = client
    url = reverse("perfil-usuario")
    payload = {"nome_completo": "Novo Nome"}
    resp = api.put(url, payload, format="json")
    assert resp.status_code == 200
    assert resp.data["nome_completo"] == "Novo Nome"


def test_trocar_senha_com_sucesso(client):
    api, user = client
    url = reverse("trocar-senha")
    payload = {"senha_atual": "Senha123!", "nova_senha": "NovaSenha456!"}
    resp = api.put(url, payload, format="json")
    assert resp.status_code == 204
    assert user.check_password("NovaSenha456!")


def test_ver_preferencias(client):
    api, _ = client
    url = reverse("ver-preferencias")
    resp = api.get(url)
    assert resp.status_code == 200
    assert "tema_escuro" in resp.data


def test_listar_nucleos(client):
    api, _ = client
    url = reverse("listar-nucleos")
    resp = api.get(url)
    assert resp.status_code == 200
    assert isinstance(resp.data, list)
