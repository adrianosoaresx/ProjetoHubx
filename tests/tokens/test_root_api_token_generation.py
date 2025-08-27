import re

import pytest
from django.urls import reverse

from accounts.factories import UserFactory
from accounts.models import UserType
from tokens.models import ApiToken

pytestmark = pytest.mark.django_db


def test_root_user_can_generate_api_token(client):
    user = UserFactory(user_type=UserType.ROOT.value)
    client.force_login(user)

    resp = client.get(reverse("tokens:listar_api_tokens"))
    assert resp.status_code == 200
    assert "Gerar Token" in resp.content.decode()

    resp = client.post(
        reverse("tokens:gerar_api_token"),
        {"scope": "admin"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Token:" in content
    match = re.search(r"<code[^>]*>([^<]+)</code>", content)
    assert match and match.group(1)
    assert ApiToken.objects.filter(user=user).exists()
