import hashlib
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.factories import UserFactory
from tokens.models import ApiToken, ApiTokenLog
from tokens.services import generate_token
from tokens.tasks import revogar_tokens_expirados, rotacionar_tokens_proximos_da_expiracao
from tokens.utils import revoke_token, rotate_token

pytestmark = pytest.mark.django_db


def test_generate_token_service():
    user = UserFactory()
    raw = generate_token(user, "cli", "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    assert token.user == user
    assert token.token_hash != raw


def test_generate_token_without_expires_in():
    user = UserFactory()
    raw = generate_token(user, "cli", "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    assert token.expires_at is None


def test_revoke_token_idempotent():
    user = UserFactory()
    raw = generate_token(user, "cli", "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    revoke_token(token.id, user, ip="1.1.1.1", user_agent="ua")
    revoke_token(token.id, user, ip="1.1.1.1", user_agent="ua")
    assert ApiTokenLog.objects.filter(token=token, acao="revogacao").count() == 1


def test_rotate_token_service():
    user = UserFactory()
    raw = generate_token(user, "cli", "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    new_raw = rotate_token(token.id, user, ip="127.0.0.1", user_agent="ua-test")
    new_hash = hashlib.sha256(new_raw.encode()).hexdigest()
    novo_token = ApiToken.objects.get(token_hash=new_hash)
    assert novo_token.anterior == token
    token_db = ApiToken.all_objects.get(id=token.id)
    assert token_db.revoked_at is not None
    assert new_raw != raw


def test_generate_token_with_device_fingerprint():
    user = UserFactory()
    fingerprint = "abc123"
    raw = generate_token(user, "cli", "read", timedelta(days=1), fingerprint)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    assert token.device_fingerprint == fingerprint


def test_revogar_tokens_expirados():
    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    token.expires_at = timezone.now() - timezone.timedelta(days=1)
    token.save(update_fields=["expires_at"])
    revogar_tokens_expirados()
    token_db = ApiToken.all_objects.get(id=token.id)
    assert token_db.revoked_at is not None
    assert token_db.deleted is True
    assert token_db.revogado_por == user
    log = ApiTokenLog.objects.get(token=token_db, acao=ApiTokenLog.Acao.REVOGACAO)
    assert log.usuario is None
    assert log.ip == "0.0.0.0"
    assert log.user_agent == "task:revogar_tokens_expirados"


def test_rotacionar_tokens_proximos_da_expiracao():
    user = UserFactory()
    raw = generate_token(user, "cli", "read", timedelta(days=1))
    token = ApiToken.objects.get(token_hash=hashlib.sha256(raw.encode()).hexdigest())

    rotacionar_tokens_proximos_da_expiracao()

    novo_token = ApiToken.objects.get(anterior=token)
    token_db = ApiToken.all_objects.get(id=token.id)

    assert token_db.revoked_at is not None
    assert ApiTokenLog.objects.filter(token=novo_token, acao="geracao").exists()
    assert ApiTokenLog.objects.filter(token=token_db, acao="revogacao").exists()
