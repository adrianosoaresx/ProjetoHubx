import pytest
from django.utils import timezone
from twilio.base.exceptions import TwilioRestException

from configuracoes.tasks import _send_for_frequency, enviar_notificacao_whatsapp

pytestmark = pytest.mark.django_db


def test_window_and_idempotence(monkeypatch, admin_user):
    called = {"email": 0, "whats": 0}

    def fake_send(user, template, ctx):
        called["email"] += 1

    def fake_whats(user_id, ctx):
        called["whats"] += 1

    monkeypatch.setattr("configuracoes.tasks.enviar_para_usuario", fake_send)
    monkeypatch.setattr("configuracoes.tasks.enviar_notificacao_whatsapp.delay", fake_whats)
    now = timezone.datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr("configuracoes.tasks.timezone.localtime", lambda: now)
    config = admin_user.configuracao
    config.frequencia_notificacoes_email = "diaria"
    config.hora_notificacao_diaria = now.time()
    config.save()
    _send_for_frequency("diaria")
    _send_for_frequency("diaria")
    assert called["email"] == 1


def test_task_has_retry():
    assert TwilioRestException in enviar_notificacao_whatsapp.autoretry_for
