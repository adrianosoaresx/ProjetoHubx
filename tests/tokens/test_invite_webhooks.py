import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from accounts.models import UserType
from nucleos.factories import NucleoFactory
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

    def fake_post(url, data, headers, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["headers"] = headers

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)

    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    nucleo = NucleoFactory(organizacao=org)
    client.force_login(user)
    data = {
        "tipo_destino": TokenAcesso.TipoUsuario.CONVIDADO,
        "organizacao": org.pk,
        "nucleos": [nucleo.pk],
    }
    client.post(reverse("tokens:gerar_convite"), data)

    token = TokenAcesso.objects.get(gerado_por=user)

    assert calls["url"] == "https://example.com/hook"
    payload = json.loads(calls["data"].decode())
    assert payload["event"] == "invite.created"
    assert payload["id"] == str(token.id)
    assert token.check_codigo(payload["code"])
    expected_sig = hmac.new(b"segredo", calls["data"], hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_use_convite_triggers_webhook(monkeypatch):
    calls: dict[str, object] = {}

    def fake_post(url, data, headers, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["headers"] = headers

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)

    admin = UserFactory(is_staff=True)
    token, _ = create_invite_token(gerado_por=admin, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("tokens_api:token-use", args=[token.pk])
    resp = client.post(url)
    assert resp.status_code == 200

    payload = json.loads(calls["data"].decode())
    assert payload == {"event": "invite.used", "id": str(token.id)}
    expected_sig = hmac.new(b"segredo", calls["data"], hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_revogar_convite_triggers_webhook(monkeypatch, client):
    calls: dict[str, object] = {}

    def fake_post(url, data, headers, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["headers"] = headers

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)

    user = UserFactory(is_staff=True, user_type=UserType.ADMIN.value)
    org = OrganizacaoFactory()
    org.users.add(user)
    client.force_login(user)
    token, _ = create_invite_token(gerado_por=user, tipo_destino=TokenAcesso.TipoUsuario.ASSOCIADO)

    client.get(reverse("tokens:revogar_convite", args=[token.id]))

    payload = json.loads(calls["data"].decode())
    assert payload == {"event": "invite.revoked", "id": str(token.id)}
    expected_sig = hmac.new(b"segredo", calls["data"], hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig
