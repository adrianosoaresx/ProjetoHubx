import hashlib
from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens import metrics as m
from tokens.models import ApiToken
from tokens.services import generate_token, revoke_token, rotate_token

pytestmark = pytest.mark.django_db


def reset_metrics():
    m.tokens_api_tokens_created_total._value.set(0)
    m.tokens_api_tokens_used_total._value.set(0)
    m.tokens_api_tokens_revoked_total._value.set(0)
    m.tokens_api_tokens_rotated_total._value.set(0)


@override_settings(ROOT_URLCONF="Hubx.urls")
def test_api_token_metrics_flow():
    reset_metrics()
    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))
    assert m.tokens_api_tokens_created_total._value.get() == 1

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    resp = client.get(reverse("tokens_api:api-token-list"))
    assert resp.status_code == 200
    assert m.tokens_api_tokens_used_total._value.get() == 1

    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)
    rotate_token(token.id, ip="127.0.0.1", user_agent="ua-test")
    assert m.tokens_api_tokens_rotated_total._value.get() == 1
    assert m.tokens_api_tokens_revoked_total._value.get() == 1

    novo_token = ApiToken.objects.get(anterior=token)
    revoke_token(novo_token.id, ip="127.0.0.1", user_agent="ua-test")
    assert m.tokens_api_tokens_revoked_total._value.get() == 2
