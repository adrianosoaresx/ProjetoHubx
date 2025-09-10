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
    resp = client.get(url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1")
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
    resp = client.get(url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="2.2.2.2")
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
    resp = client.get(url, REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="4.4.4.4")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_api_token_ip_crud():
    owner = UserFactory()
    raw = generate_token(owner, None, "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)

    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse("tokens_api:api-token-ip-list")

    resp = client.get(url, {"token": str(token.id)})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post(
        url,
        {"token": str(token.id), "ip": "5.5.5.5", "tipo": ApiTokenIp.Tipo.PERMITIDO},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    ip_id = resp.json()["id"]

    resp = client.get(url, {"token": str(token.id)})
    assert len(resp.json()) == 1

    resp = client.delete(reverse("tokens_api:api-token-ip-detail", args=[ip_id]))
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    resp = client.get(url, {"token": str(token.id)})
    assert resp.json() == []


def test_api_token_ip_permissions():
    owner = UserFactory()
    other = UserFactory()
    raw = generate_token(owner, None, "read")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)

    ip_obj = ApiTokenIp.objects.create(token=token, ip="7.7.7.7", tipo=ApiTokenIp.Tipo.PERMITIDO)

    client = APIClient()
    client.force_authenticate(user=other)
    url = reverse("tokens_api:api-token-ip-list")

    resp = client.post(
        url,
        {"token": str(token.id), "ip": "8.8.8.8", "tipo": ApiTokenIp.Tipo.PERMITIDO},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    resp = client.delete(reverse("tokens_api:api-token-ip-detail", args=[ip_obj.id]))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
