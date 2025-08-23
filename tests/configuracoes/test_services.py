import uuid

import pytest
from django.core.cache import cache

from configuracoes import metrics
from configuracoes.models import ConfiguracaoContextual
from configuracoes.services import (
    atualizar_preferencias_usuario,
    get_configuracao_conta,
    get_user_preferences,
)

pytestmark = pytest.mark.django_db


def test_atualizar_preferencias_usuario(admin_user):
    cache.clear()
    atualizar_preferencias_usuario(admin_user, {"tema": "escuro"})
    config = get_configuracao_conta(admin_user)
    assert config.tema == "escuro"


def test_get_configuracao_conta_recupera_soft_deleted(admin_user):
    cache.clear()
    config = admin_user.configuracao
    config.delete()

    recuperado = get_configuracao_conta(admin_user)
    assert recuperado.pk == config.pk
    assert recuperado.deleted is False


def test_metrics_cache(admin_user):
    cache.clear()
    metrics.config_cache_hits_total._value.set(0)  # reset
    metrics.config_cache_misses_total._value.set(0)
    get_configuracao_conta(admin_user)
    assert metrics.config_cache_misses_total._value.get() == 1
    get_configuracao_conta(admin_user)
    assert metrics.config_cache_hits_total._value.get() == 1


@pytest.mark.parametrize("escopo", ["organizacao", "nucleo", "evento"])
def test_get_user_preferences_contextual(admin_user, escopo):
    cache.clear()
    escopo_id = uuid.uuid4()
    ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo=escopo,
        escopo_id=escopo_id,
        tema="escuro",
        receber_notificacoes_email=False,

        frequencia_notificacoes_email="semanal",
        receber_notificacoes_whatsapp=True,
        frequencia_notificacoes_whatsapp="diaria",

        receber_notificacoes_push=False,
        frequencia_notificacoes_push="semanal",
    )
    prefs = get_user_preferences(admin_user, escopo, str(escopo_id))
    assert prefs.tema == "escuro"
    assert prefs.receber_notificacoes_email is False

    assert prefs.frequencia_notificacoes_email == "semanal"
    assert prefs.receber_notificacoes_whatsapp is True
    assert prefs.frequencia_notificacoes_whatsapp == "diaria"

    assert prefs.receber_notificacoes_push is False
    assert prefs.frequencia_notificacoes_push == "semanal"
    prefs_global = get_user_preferences(admin_user)
    assert prefs_global.tema == admin_user.configuracao.tema
    assert (
        prefs_global.receber_notificacoes_email
        == admin_user.configuracao.receber_notificacoes_email
    )
    assert (
        prefs_global.frequencia_notificacoes_email
        == admin_user.configuracao.frequencia_notificacoes_email
    )
    assert (
        prefs_global.receber_notificacoes_whatsapp
        == admin_user.configuracao.receber_notificacoes_whatsapp
    )
    assert (
        prefs_global.frequencia_notificacoes_whatsapp
        == admin_user.configuracao.frequencia_notificacoes_whatsapp
    )
    assert (
        prefs_global.receber_notificacoes_push
        == admin_user.configuracao.receber_notificacoes_push
    )
    assert (
        prefs_global.frequencia_notificacoes_push
        == admin_user.configuracao.frequencia_notificacoes_push
    )


def test_get_user_preferences_fallback_to_global(admin_user):
    cache.clear()
    config = admin_user.configuracao
    config.tema = "escuro"
    config.receber_notificacoes_email = True
    config.frequencia_notificacoes_email = "diaria"
    config.idioma = "en-US"
    config.save()
    escopo_id = uuid.uuid4()
    ConfiguracaoContextual.objects.create(
        user=admin_user,
        escopo_tipo="organizacao",
        escopo_id=escopo_id,
        tema="automatico",
        receber_notificacoes_email=None,
        frequencia_notificacoes_email=None,
        idioma=None,
    )
    prefs = get_user_preferences(admin_user, "organizacao", str(escopo_id))
    assert prefs.tema == "automatico"
    assert prefs.receber_notificacoes_email is True
    assert prefs.frequencia_notificacoes_email == "diaria"
    assert prefs.idioma == "en-US"
