import hashlib
import hmac
import json
from datetime import timedelta

import pytest
from django.test import override_settings

from accounts.factories import UserFactory
from tokens.models import ApiToken
from tokens.services import generate_token
from tokens.utils import revoke_token, rotate_token


pytestmark = pytest.mark.django_db


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_generate_token_triggers_webhook(monkeypatch):
    calls: dict[str, object] = {}

    def fake_post(url, data, headers, timeout):
        calls["url"] = url
        calls["data"] = data
        calls["headers"] = headers

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)
    monkeypatch.setattr("tokens.tasks.requests.post", fake_post)

    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))

    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    token = ApiToken.objects.get(token_hash=token_hash)

    assert calls["url"] == "https://example.com/hook"
    assert json.loads(calls["data"].decode()) == {
        "event": "created",
        "id": str(token.id),
        "token": token_hash,
    }

    expected_sig = hmac.new(b"segredo", calls["data"], hashlib.sha256).hexdigest()
    assert calls["headers"]["X-Hubx-Signature"] == expected_sig


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="segredo",
)
def test_revoke_token_triggers_webhook(monkeypatch):
    calls: list[tuple[str, bytes, dict[str, str]]] = []

    def fake_post(url, data, headers, timeout):
        calls.append((url, data, headers))

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)
    monkeypatch.setattr("tokens.tasks.requests.post", fake_post)

    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))
    token = ApiToken.objects.get(token_hash=hashlib.sha256(raw.encode()).hexdigest())

    calls.clear()  # ignora webhook de criação

    revoke_token(token.id, ip="1.1.1.1", user_agent="tests")

    assert len(calls) == 1
    url, data, headers = calls[0]
    assert url == "https://example.com/hook"
    assert json.loads(data.decode()) == {"event": "revoked", "id": str(token.id)}
    expected_sig = hmac.new(b"segredo", data, hashlib.sha256).hexdigest()
    assert headers["X-Hubx-Signature"] == expected_sig


@override_settings(
    TOKENS_WEBHOOK_URL="https://example.com/hook",
    TOKEN_WEBHOOK_SECRET="",
)
def test_rotate_token_triggers_webhook(monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_post(url, data, headers, timeout):
        calls.append(json.loads(data.decode()))

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr("tokens.services.requests.post", fake_post)
    monkeypatch.setattr("tokens.tasks.requests.post", fake_post)

    user = UserFactory()
    raw = generate_token(user, None, "read", timedelta(days=1))
    token = ApiToken.objects.get(token_hash=hashlib.sha256(raw.encode()).hexdigest())

    calls.clear()

    rotate_token(token.id, user, ip="1.1.1.1", user_agent="tests")

    events = {c["event"] for c in calls}
    assert {"created", "revoked", "rotated"} <= events
    assert any(c.get("event") == "rotated" and c.get("id") == str(token.id) for c in calls)
