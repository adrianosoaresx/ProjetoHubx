
import pytest

import hashlib

from datetime import timedelta

import hashlib
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens.models import ApiToken, ApiTokenLog
from tokens.services import generate_token, revoke_token
from tokens.tasks import revogar_tokens_expirados

pytestmark = pytest.mark.django_db


def test_generate_token_service():
    user = UserFactory()
    raw = generate_token(user, "cli", "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    assert token.user == user
    assert token.token_hash != raw


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_api_token_authentication_and_revocation():
    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    url = reverse("tokens_api:api-token-list")
    assert client.get(url, HTTP_USER_AGENT="ua-test").status_code == 200

    token = ApiToken.objects.get(token_hash=token_hash)

    usage_log = ApiTokenLog.objects.get(token=token, acao="uso")
    assert usage_log.user_agent == "ua-test"
    assert usage_log.ip == "127.0.0.1"
    revoke_token(token.id)

    token_db = ApiToken.all_objects.get(id=token.id)
    assert token_db.deleted is True
    assert token_db.revoked_at is not None
    assert token_db.revogado_por == user
    resp = client.get(url)
    assert resp.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


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


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_api_view_create_and_destroy():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:api-token-list")
    resp = client.post(
        url,
        {"scope": "read", "expires_in": 1},
        HTTP_USER_AGENT="ua-create",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    token_id = resp.data["id"]
    assert "token" in resp.data
    token = ApiToken.objects.get(id=token_id)
    log = ApiTokenLog.objects.get(token=token, acao="geracao")
    assert log.user_agent == "ua-create"
    assert log.ip == "127.0.0.1"

    list_resp = client.get(url, HTTP_USER_AGENT="ua-list")
    assert list_resp.status_code == 200

    del_resp = client.delete(
        reverse("tokens_api:api-token-detail", args=[token_id]),
        HTTP_USER_AGENT="ua-delete",
    )
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    assert ApiTokenLog.objects.filter(token=token, acao="revogacao").exists()

    token_db = ApiToken.all_objects.get(id=token_id)
    assert token_db.revogado_por == user

