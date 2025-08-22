import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens.factories import TokenAcessoFactory
from tokens.models import TokenAcesso, TokenUsoLog

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.urls_tokens")]


def _validate(client, code, ip="1.1.1.1", ua="test-agent"):
    url = reverse("tokens_api:token-validate") + f"?codigo={code}"
    return client.get(url, REMOTE_ADDR=ip, HTTP_USER_AGENT=ua)


def _setup_client(user=None):
    client = APIClient()
    if user is None:
        user = UserFactory()
    client.force_authenticate(user=user)
    return client


def test_log_on_invalid_code():
    client = _setup_client()
    invalid_code = TokenAcesso.generate_code()
    resp = _validate(client, invalid_code)
    assert resp.status_code == 404
    log = TokenUsoLog.objects.get()
    assert log.acao == TokenUsoLog.Acao.VALIDACAO
    assert log.token is None
    assert log.ip == "1.1.1.1"
    assert log.user_agent == "test-agent"


def test_log_on_revoked_token():
    token = TokenAcessoFactory(estado=TokenAcesso.Estado.REVOGADO)
    client = _setup_client()
    resp = _validate(client, token.codigo)
    assert resp.status_code == 409
    log = TokenUsoLog.objects.get()
    assert log.token == token
    assert log.acao == TokenUsoLog.Acao.VALIDACAO
    assert log.ip == "1.1.1.1"
    assert log.user_agent == "test-agent"


def test_log_on_invalid_state_token():
    token = TokenAcessoFactory(estado=TokenAcesso.Estado.USADO)
    client = _setup_client()
    resp = _validate(client, token.codigo)
    assert resp.status_code == 409
    log = TokenUsoLog.objects.get()
    assert log.token == token
    assert log.acao == TokenUsoLog.Acao.VALIDACAO


def test_log_on_expired_token():
    token = TokenAcessoFactory(
        estado=TokenAcesso.Estado.NOVO,
        data_expiracao=timezone.now() - timezone.timedelta(days=1),
    )
    client = _setup_client()
    resp = _validate(client, token.codigo)
    assert resp.status_code == 409
    token.refresh_from_db()
    assert token.estado == TokenAcesso.Estado.EXPIRADO
    log = TokenUsoLog.objects.get()
    assert log.token == token
    assert log.acao == TokenUsoLog.Acao.VALIDACAO
