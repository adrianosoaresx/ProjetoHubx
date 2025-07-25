import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens.models import TokenAcesso, TokenUsoLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_limite_diario(api_client):
    user = UserFactory(is_staff=True)
    api_client.force_authenticate(user=user)
    url = reverse("tokens_api:token-list")
    for _ in range(5):
        resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
        assert resp.status_code == status.HTTP_201_CREATED
    resp = api_client.post(url, {"tipo_destino": TokenAcesso.TipoUsuario.ASSOCIADO})
    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_registro_logs(api_client):
    user = UserFactory(is_staff=True)
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
    token = TokenAcesso.objects.create(gerado_por=admin, tipo_destino=TokenAcesso.TipoUsuario.ADMIN)
    url = reverse("tokens_api:token-revoke", args=[token.pk])
    resp = api_client.post(url)
    assert resp.status_code == 200
    token.refresh_from_db()
    assert token.estado == TokenAcesso.Estado.REVOGADO
    assert TokenUsoLog.objects.filter(token=token, acao="revogacao").exists()

    # tentativa de uso apos revogacao
    use_url = reverse("tokens_api:token-use", args=[token.pk])
    resp = api_client.post(use_url)
    assert resp.status_code == status.HTTP_409_CONFLICT
