import uuid
from types import SimpleNamespace

import pytest
from django.test import override_settings
import requests

from tokens import services
from tokens.models import TokenWebhookEvent


@override_settings(TOKENS_WEBHOOK_URL="http://example.com")
@pytest.mark.django_db
def test_send_webhook_retry_success(monkeypatch):
    calls = []

    def fake_post(url, data, headers, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise requests.RequestException("boom")
        return SimpleNamespace(status_code=200)

    sleeps: list[int] = []
    monkeypatch.setattr("tokens.services.requests.post", fake_post)
    monkeypatch.setattr("tokens.services.time.sleep", lambda s: sleeps.append(s))

    token = SimpleNamespace(id=uuid.uuid4())
    services.token_created(token, "raw")

    assert len(calls) == 3
    assert sleeps == [1, 2]
    assert TokenWebhookEvent.objects.count() == 0


@override_settings(TOKENS_WEBHOOK_URL="http://example.com")
@pytest.mark.django_db
def test_send_webhook_logs_failure(monkeypatch):
    def fake_post(url, data, headers, timeout):
        raise requests.RequestException("boom")

    sleeps: list[int] = []
    monkeypatch.setattr("tokens.services.requests.post", fake_post)
    monkeypatch.setattr("tokens.services.time.sleep", lambda s: sleeps.append(s))

    token = SimpleNamespace(id=uuid.uuid4())
    services.token_created(token, "raw")

    event = TokenWebhookEvent.objects.get()
    assert event.url == "http://example.com"
    assert event.attempts == 3
    assert sleeps == [1, 2]
