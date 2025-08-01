import pytest
from django.core.cache import cache

from configuracoes.services import atualizar_preferencias_usuario, get_configuracao_conta

pytestmark = pytest.mark.django_db


def test_atualizar_preferencias_usuario(admin_user):
    cache.clear()
    atualizar_preferencias_usuario(admin_user, {"tema": "escuro"})
    config = get_configuracao_conta(admin_user)
    assert config.tema == "escuro"
