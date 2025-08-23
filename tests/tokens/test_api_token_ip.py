import hashlib

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens.models import ApiToken, ApiTokenIp
from tokens.services import generate_token

pytestmark = pytest.mark.django_db


def test_token_authentication_allowed_ip():
    user = UserFactory()
    raw = generate_token(user, None, "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    ApiTokenIp.objects.create(token=token, ip="1.1.1.1", tipo=ApiTokenIp.Tipo.PERMITIDO)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    url = reverse("tokens_api:api-token-list")
    resp = client.get(
        url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1"
    )
    assert resp.status_code == 200


def test_token_authentication_blocked_ip():
    user = UserFactory()
    raw = generate_token(user, None, "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    ApiTokenIp.objects.create(token=token, ip="2.2.2.2", tipo=ApiTokenIp.Tipo.NEGADO)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    url = reverse("tokens_api:api-token-list")
    resp = client.get(
        url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="2.2.2.2"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_token_authentication_not_in_allowed_list():
    user = UserFactory()
    raw = generate_token(user, None, "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    ApiTokenIp.objects.create(token=token, ip="3.3.3.3", tipo=ApiTokenIp.Tipo.PERMITIDO)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    url = reverse("tokens_api:api-token-list")
    resp = client.get(
        url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="4.4.4.4"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
