from __future__ import annotations

import pytest

from configuracoes.forms import ConfiguracaoContaForm

pytestmark = pytest.mark.django_db


def test_form_fields():
    form = ConfiguracaoContaForm()
    assert list(form.fields.keys()) == [
        "receber_notificacoes_email",
        "frequencia_notificacoes_email",
        "receber_notificacoes_whatsapp",
        "frequencia_notificacoes_whatsapp",
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
    assert config.idioma == "en-US"
    assert config.tema == "escuro"


def test_form_boolean_coercion(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": "on",
        "frequencia_notificacoes_email": "imediata",
        "frequencia_notificacoes_whatsapp": "imediata",
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
