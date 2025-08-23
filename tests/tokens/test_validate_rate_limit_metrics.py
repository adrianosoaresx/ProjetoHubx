import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.test import override_settings
from django_redis import get_redis_connection

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens import metrics as m
from tokens.models import TokenAcesso
from tokens.services import create_invite_token

pytestmark = pytest.mark.django_db


@override_settings(TOKENS_RATE_LIMITS={"burst": (1, 60)})
def test_validate_ratelimit_increments_metric():
    try:
        get_redis_connection("default").flushall()
    except Exception:
        from django.core.cache import cache
        cache.clear()
    m.tokens_rate_limited_total._value.set(0)

    user = UserFactory(user_type=UserType.ADMIN.value)
    client = APIClient()
    client.force_authenticate(user=user)
    token, codigo = create_invite_token(
        gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO
    )
    url = reverse("tokens_api:token-validate") + f"?codigo={codigo}"

    resp1 = client.get(url)
    assert resp1.status_code == 200

    resp2 = client.get(url)
    assert resp2.status_code == 429
    assert "Retry-After" in resp2.headers
    assert m.tokens_rate_limited_total._value.get() == 1
