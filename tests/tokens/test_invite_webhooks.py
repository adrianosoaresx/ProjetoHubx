import hashlib
import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from organizacoes.factories import OrganizacaoFactory
from tokens.models import TokenAcesso
from tokens.services import create_invite_token


pytestmark = pytest.mark.django_db


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_gerar_convite_triggers_webhook(monkeypatch, client):
    calls: dict[str, object] = {}

    def fake_send(payload):
        calls["payload"] = payload
        calls["url"] = "https://example.com/hook"
        calls["headers"] = {
            "X-Hubx-Signature": hmac.new(b"segredo", json.dumps(payload).encode(), hashlib.sha256).hexdigest()
        }

    monkeypatch.setattr("tokens.services._send_webhook", fake_send)

    org = OrganizacaoFactory()
    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value, organizacao=org)
    org.users.add(user)
    client.force_login(user)
    data = {
        "tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO.value,
        "organizacao": org.pk,
    }
    client.post(reverse("tokens:gerar_convite"), data)

    token = TokenAcesso.objects.get(gerado_por=user)

    assert calls["url"] == "https://example.com/hook"
    payload = calls["payload"]
    assert payload["event"] == "invite.created"
    assert payload["id"] == str(token.id)
    assert token.check_codigo(payload["code"])
    expected_sig = hmac.new(b"segredo", json.dumps(payload).encode(), hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_use_convite_triggers_webhook(monkeypatch):
    calls: dict[str, object] = {}

    def fake_send(payload):
        calls["payload"] = payload
        calls["url"] = "https://example.com/hook"
        calls["headers"] = {
            "X-Hubx-Signature": hmac.new(b"segredo", json.dumps(payload).encode(), hashlib.sha256).hexdigest()
        }

    monkeypatch.setattr("tokens.services._send_webhook", fake_send)

    admin_org = OrganizacaoFactory()
    admin = UserFactory(is_staff=True, user_type=UserType.ADMIN.value, organizacao=admin_org)
    token, _ = create_invite_token(
        gerado_por=admin,
        tipo_destino=TokenAcesso.TipoUsuario.CONVIDADO.value,
        organizacao=admin_org,
    )
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:token-use", args=[token.pk])
    resp = client.post(url)
    assert resp.status_code == 200

    payload = calls["payload"]
    assert payload == {"event": "invite.used", "id": str(token.id)}
    expected_sig = hmac.new(b"segredo", json.dumps(payload).encode(), hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig


 
