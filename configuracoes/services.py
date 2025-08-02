from __future__ import annotations

from typing import Any

from django.core.cache import cache

from accounts.models import User

from .models import ConfiguracaoConta

CACHE_KEY = "configuracao_conta:{id}"


def get_configuracao_conta(usuario: User) -> ConfiguracaoConta:
    """Obtém configurações do cache ou do banco com chave única por usuário."""
    key = CACHE_KEY.format(id=usuario.id)
    config = cache.get(key)
    if config is None:
        config, _ = ConfiguracaoConta.objects.get_or_create(user_id=usuario.id, defaults={"user": usuario})
        cache.set(key, config)
    return config


def atualizar_preferencias_usuario(usuario: User, dados: dict[str, Any]) -> ConfiguracaoConta:
    """Atualiza as preferências do usuário e invalida o cache."""
    config = get_configuracao_conta(usuario)
    for field, value in dados.items():
        if hasattr(config, field):
            setattr(config, field, value)
    config.save()
    cache.set(CACHE_KEY.format(id=usuario.id), config)
    return config
