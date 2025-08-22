import uuid
from types import SimpleNamespace

import pytest
from django.test import override_settings
import requests

from tokens import services
from tokens.models import TokenWebhookEvent
from tokens.tasks import reenviar_webhooks_pendentes, send_webhook


@override_settings(TOKENS_WEBHOOK_URL="http://example.com")
@pytest.mark.django_db
def test_enqueue_webhook_task(monkeypatch):
    queued: list[dict[str, object]] = []
    monkeypatch.setattr(
        "tokens.services.send_webhook.delay", lambda payload: queued.append(payload)
    )

    token = SimpleNamespace(id=uuid.uuid4())
    services.token_created(token, "raw")

    assert queued == [{"event": "created", "id": str(token.id), "token": "raw"}]


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
    monkeypatch.setattr("tokens.tasks.requests.post", fake_post)
    monkeypatch.setattr("tokens.tasks.time.sleep", lambda s: sleeps.append(s))

    send_webhook.run({"event": "created"})

    assert len(calls) == 3
    assert sleeps == [1, 2]
    assert TokenWebhookEvent.objects.count() == 0


@override_settings(TOKENS_WEBHOOK_URL="http://example.com")
@pytest.mark.django_db
def test_send_webhook_logs_failure(monkeypatch):
    def fake_post(url, data, headers, timeout):
        raise requests.RequestException("boom")

    sleeps: list[int] = []
    monkeypatch.setattr("tokens.tasks.requests.post", fake_post)
    monkeypatch.setattr("tokens.tasks.time.sleep", lambda s: sleeps.append(s))

    send_webhook.run({"event": "created"})

    event = TokenWebhookEvent.objects.get()
    assert event.url == "http://example.com"
    assert event.attempts == 3
    assert sleeps == [1, 2]


@pytest.mark.django_db
def test_reenviar_webhooks_pendentes(monkeypatch):
    event = TokenWebhookEvent.objects.create(
        url="http://example.com",
        payload={"event": "created"},
        delivered=False,
    )

    monkeypatch.setattr(
        "tokens.tasks.requests.post", lambda url, data, headers, timeout: SimpleNamespace(status_code=200)
    )

    reenviar_webhooks_pendentes.run()

    event.refresh_from_db()
    assert event.delivered is True
    assert event.attempts == 0
