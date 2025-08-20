from __future__ import annotations

import pytest

from configuracoes.forms import ConfiguracaoContaForm
from unittest.mock import MagicMock

pytestmark = pytest.mark.django_db


def test_form_fields():
    form = ConfiguracaoContaForm()
    assert list(form.fields.keys()) == [
        "receber_notificacoes_email",
        "frequencia_notificacoes_email",
        "receber_notificacoes_whatsapp",
        "frequencia_notificacoes_whatsapp",
        "receber_notificacoes_push",
        "frequencia_notificacoes_push",
        "idioma",
        "tema",
        "hora_notificacao_diaria",
        "hora_notificacao_semanal",
        "dia_semana_notificacao",
    ]


def test_form_valid_data(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": False,
        "frequencia_notificacoes_email": "diaria",
        "receber_notificacoes_whatsapp": True,
        "frequencia_notificacoes_whatsapp": "semanal",
        "receber_notificacoes_push": True,
        "frequencia_notificacoes_push": "imediata",
        "idioma": "en-US",
        "tema": "escuro",
        "hora_notificacao_diaria": "08:00",
        "hora_notificacao_semanal": "09:00",
        "dia_semana_notificacao": 1,
    }
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert form.is_valid()
    obj = form.save()
    config.refresh_from_db()
    assert obj == config
    assert config.receber_notificacoes_email is False
    assert config.frequencia_notificacoes_email == "imediata"
    assert config.receber_notificacoes_whatsapp is True
    assert config.frequencia_notificacoes_whatsapp == "semanal"
    assert config.receber_notificacoes_push is True
    assert config.frequencia_notificacoes_push == "imediata"
    assert config.idioma == "en-US"
    assert config.tema == "escuro"


def test_form_boolean_coercion(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": "on",
        "frequencia_notificacoes_email": "imediata",
        "frequencia_notificacoes_whatsapp": "imediata",
        "receber_notificacoes_push": "on",
        "frequencia_notificacoes_push": "imediata",
        "idioma": "pt-BR",
        "tema": "claro",
        "hora_notificacao_diaria": "08:00",
        "hora_notificacao_semanal": "08:00",
        "dia_semana_notificacao": 0,
    }
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert form.is_valid()
    form.save()
    config.refresh_from_db()
    assert config.receber_notificacoes_email is True
    assert config.receber_notificacoes_whatsapp is False
    assert config.receber_notificacoes_push is True
    assert config.receber_notificacoes_push is True


def test_form_requires_daily_time(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": True,
        "frequencia_notificacoes_email": "diaria",
        "frequencia_notificacoes_whatsapp": "imediata",
        "receber_notificacoes_push": True,
        "frequencia_notificacoes_push": "imediata",
        "idioma": "pt-BR",
        "tema": "claro",
        "hora_notificacao_diaria": "",
        "hora_notificacao_semanal": "08:00",
        "dia_semana_notificacao": 0,
    }
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert not form.is_valid()
    assert "hora_notificacao_diaria" in form.errors


def test_form_requires_weekly_fields(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": True,
        "frequencia_notificacoes_email": "imediata",
        "frequencia_notificacoes_whatsapp": "imediata",
        "receber_notificacoes_push": True,
        "frequencia_notificacoes_push": "semanal",
        "idioma": "pt-BR",
        "tema": "claro",
        "hora_notificacao_diaria": "08:00",
        "hora_notificacao_semanal": "",
        "dia_semana_notificacao": "",
    }
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert not form.is_valid()
    assert "hora_notificacao_semanal" in form.errors
    assert "dia_semana_notificacao" in form.errors


def test_testar_whatsapp_api(client, admin_user, settings, monkeypatch):
    settings.CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"
    settings.ROOT_URLCONF = "Hubx.urls"
    admin_user.configuracao.receber_notificacoes_whatsapp = True
    admin_user.configuracao.save(update_fields=["receber_notificacoes_whatsapp"])
    import configuracoes.api as api
    mock_send = MagicMock()
    monkeypatch.setattr(api, "send_whatsapp", mock_send)
    client.force_login(admin_user)
    response = client.post("/api/configuracoes/testar/", {"canal": "whatsapp"})
    assert response.status_code == 200
    assert response.json()["detail"] == "enviado"
    mock_send.assert_called_once_with(admin_user, "Mensagem de teste")


def test_testar_whatsapp_api_indisponivel(client, admin_user, settings, monkeypatch):
    settings.CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"
    settings.ROOT_URLCONF = "Hubx.urls"
    admin_user.configuracao.receber_notificacoes_whatsapp = True
    admin_user.configuracao.save(update_fields=["receber_notificacoes_whatsapp"])
    import configuracoes.api as api

    def fake_send(user, msg):
        raise RuntimeError("WhatsApp indisponível")

    monkeypatch.setattr(api, "send_whatsapp", fake_send)
    client.force_login(admin_user)
    response = client.post("/api/configuracoes/testar/", {"canal": "whatsapp"})
    assert response.status_code == 503
    assert response.json()["detail"] == "WhatsApp indisponível"
