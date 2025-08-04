import pytest
from django.core.cache import cache

from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta

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
