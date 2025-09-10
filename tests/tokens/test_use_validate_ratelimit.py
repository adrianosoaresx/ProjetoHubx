import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens.models import TokenAcesso
from tokens.services import create_invite_token

pytestmark = pytest.mark.django_db


def test_use_validate_ratelimit():
    user = UserFactory(user_type=UserType.ADMIN.value)
    client = APIClient()
    client.force_authenticate(user=user)
    token, codigo = create_invite_token(gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)
    url = reverse("tokens_api:token-validate") + f"?codigo={codigo}"
    for _ in range(10):
        resp = client.get(url)
        assert resp.status_code == 200
    resp = client.get(url)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
