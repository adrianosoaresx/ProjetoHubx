from __future__ import annotations

import pytest

from configuracoes.forms import ConfiguracaoContaForm

pytestmark = pytest.mark.django_db


def test_form_fields():
    form = ConfiguracaoContaForm()
    assert list(form.fields.keys()) == [
        "receber_notificacoes_email",
        "receber_notificacoes_whatsapp",
        "tema_escuro",
    ]


def test_form_valid_data(admin_user):
    config = admin_user.configuracao
    data = {
        "receber_notificacoes_email": False,
        "receber_notificacoes_whatsapp": True,
        "tema_escuro": True,
    }
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert form.is_valid()
    obj = form.save()
    config.refresh_from_db()
    assert obj == config
    assert config.receber_notificacoes_email is False
    assert config.receber_notificacoes_whatsapp is True
    assert config.tema_escuro is True


def test_form_boolean_coercion(admin_user):
    config = admin_user.configuracao
    data = {"receber_notificacoes_email": "on"}
    form = ConfiguracaoContaForm(data=data, instance=config)
    assert form.is_valid()
    form.save()
    config.refresh_from_db()
    assert config.receber_notificacoes_email is True
    assert config.receber_notificacoes_whatsapp is False
    assert config.tema_escuro is False
