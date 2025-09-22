import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from organizacoes.factories import OrganizacaoFactory
from tokens.models import TokenAcesso, TokenUsoLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_limite_diario(api_client):
    user = UserFactory(is_staff=True)
    org = OrganizacaoFactory()
    org.users.add(user)
    api_client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    for _ in range(5):
        resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
        assert resp.status_code == status.HTTP_201_CREATED
    resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_registro_logs(api_client):
    user = UserFactory(is_staff=True)
    org = OrganizacaoFactory()
    org.users.add(user)
    api_client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
    token_id = resp.data["id"]
    token = TokenAcesso.objects.get(id=token_id)
    assert TokenUsoLog.objects.filter(token=token, acao="geracao").exists()

    validate_url = reverse("tokens_api:token-validate") + f"?codigo={token.codigo}"
    resp = api_client.get(validate_url)
    assert resp.status_code == 200
    assert TokenUsoLog.objects.filter(token=token, acao="validacao").exists()


def test_revogar_token(api_client):
    admin = UserFactory(is_staff=True)
    api_client.force_authenticate(user=admin)
    token = TokenAcesso.objects.create(gerado_por=admin, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)
    url = reverse("tokens_api:token-revogar", kwargs={"codigo": token.codigo})
    resp = api_client.post(url)
    assert resp.status_code == 200
    token.refresh_from_db()
    assert token.estado == TokenAcesso.Estado.REVOGADO
    assert TokenUsoLog.objects.filter(token=token, acao="revogacao").exists()

    # tentativa de uso apos revogacao
    use_url = reverse("tokens_api:token-use", args=[token.pk])
    resp = api_client.post(use_url)
    assert resp.status_code == status.HTTP_409_CONFLICT


def test_api_respeita_organizacao_do_usuario(api_client):
    user = UserFactory(is_staff=True)
    org = OrganizacaoFactory()
    outra = OrganizacaoFactory()
    org.users.add(user)
    api_client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = api_client.post(
        url,
        {
            "tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO,
            "organizacao": outra.pk,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    token = TokenAcesso.objects.get(gerado_por=user)
    assert token.organizacao == org


def test_api_sem_organizacao_retorna_erro(api_client):
    user = UserFactory(is_staff=True)
    api_client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "organização" in resp.data["detail"].lower()
