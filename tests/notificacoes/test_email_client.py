import logging

import pytest

from accounts.factories import UserFactory
from notificacoes.services.email_client import send_email


@pytest.mark.django_db
def test_send_email_disabled(settings, monkeypatch, caplog):
    settings.EMAIL_DELIVERY_ENABLED = False
    user = UserFactory()

    called = {"count": 0}

    def fake_send_mail(*args, **kwargs):
        called["count"] += 1

    monkeypatch.setattr(
        "notificacoes.services.email_client.send_mail",
        fake_send_mail,
    )

    with caplog.at_level(logging.INFO):
        send_email(user, "Assunto", "Corpo")

    assert called["count"] == 0
    assert any(record.message == "email_desativado" for record in caplog.records)


@pytest.mark.django_db
def test_send_email_enabled_success(settings, monkeypatch, caplog):
    settings.EMAIL_DELIVERY_ENABLED = True
    user = UserFactory()

    called = {"count": 0}

    def fake_send_mail(*args, **kwargs):
        called["count"] += 1

    monkeypatch.setattr(
        "notificacoes.services.email_client.send_mail",
        fake_send_mail,
    )

    with caplog.at_level(logging.INFO):
        send_email(user, "Assunto", "Corpo")

    assert called["count"] == 1
    assert any(record.message == "email_enviado" for record in caplog.records)


@pytest.mark.django_db
def test_send_email_enabled_failure(settings, monkeypatch, caplog):
    settings.EMAIL_DELIVERY_ENABLED = True
    user = UserFactory()

    def fake_send_mail(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(
        "notificacoes.services.email_client.send_mail",
        fake_send_mail,
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            send_email(user, "Assunto", "Corpo")

    assert any(record.message == "erro_email" for record in caplog.records)
