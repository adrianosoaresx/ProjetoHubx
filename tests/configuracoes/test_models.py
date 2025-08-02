from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from configuracoes.models import ConfiguracaoConta

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_configuracao_criada_automaticamente(admin_user):
    assert ConfiguracaoConta.objects.filter(user=admin_user).exists()


def test_configuracao_valores_padrao(admin_user):
    config = admin_user.configuracao
    assert config.receber_notificacoes_email is True
    assert config.frequencia_notificacoes_email == "imediata"
    assert config.receber_notificacoes_whatsapp is False
    assert config.frequencia_notificacoes_whatsapp == "imediata"
    assert config.idioma == "pt-BR"
    assert config.tema == "claro"


def test_configuracao_unica_por_usuario(admin_user):
    with pytest.raises(IntegrityError):
        ConfiguracaoConta.objects.create(user=admin_user)


def test_sync_preferencias(admin_user):
    config = admin_user.configuracao
    config.receber_notificacoes_email = False
    config.receber_notificacoes_whatsapp = True
    config.save()
    pref = admin_user.preferencias_notificacoes.get()
    assert pref.email is False
    assert pref.whatsapp is True
