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
    )
    prefs = get_user_preferences(admin_user, escopo, str(escopo_id))
    assert prefs.tema == "escuro"
    prefs_global = get_user_preferences(admin_user)
    assert prefs_global.tema == admin_user.configuracao.tema
