import pytest
from django.urls import reverse
from django.test import override_settings
from django_redis import get_redis_connection
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from tokens.services import generate_token


pytestmark = pytest.mark.django_db


@override_settings(TOKENS_RATE_LIMITS={"burst": (1, 60)})
def test_api_token_auth_ratelimit():
    try:
        get_redis_connection("default").flushall()
    except Exception:
        from django.core.cache import cache

        cache.clear()

    user = UserFactory()
    raw_token = generate_token(user, client_name="test", scope="read")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")

    url = reverse("tokens_api:api-token-list")
    resp1 = client.get(url)
    assert resp1.status_code == 200

    resp2 = client.get(url)
    assert resp2.status_code == 429
    assert "Retry-After" in resp2.headers
