from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

import sentry_sdk
from django.core.cache import cache

from accounts.models import User

from . import metrics
from .models import ConfiguracaoConta

CACHE_KEY = "configuracao_conta:{id}"


def get_configuracao_conta(usuario: User) -> ConfiguracaoConta:
    """Obtém configurações do cache ou do banco com chave única por usuário."""
    start = time.monotonic()
    key = CACHE_KEY.format(id=usuario.id)
    config = cache.get(key)
    if config is None or getattr(config, "deleted", False):
        metrics.config_cache_misses_total.inc()
        try:
            config, _ = ConfiguracaoConta.all_objects.select_related("user").get_or_create(
                user_id=usuario.id, defaults={"user": usuario}
            )
            if config.deleted:
                config.deleted = False
                config.deleted_at = None
                config.save(update_fields=["deleted", "deleted_at"])
            cache.set(key, config)
        except Exception as exc:  # pragma: no cover - falha de infraestrutura
            sentry_sdk.capture_exception(exc)
            raise
    else:
        metrics.config_cache_hits_total.inc()
    metrics.config_get_latency_seconds.observe(time.monotonic() - start)
    return config


def get_user_preferences(
    usuario: User, escopo_tipo: str | None = None, escopo_id: str | None = None
) -> ConfiguracaoConta:
    """Retorna sempre as preferências globais do usuário."""
    return deepcopy(get_configuracao_conta(usuario))


def atualizar_preferencias_usuario(usuario: User, dados: dict[str, Any]) -> ConfiguracaoConta:
    """Atualiza as preferências do usuário e invalida o cache."""
    config = get_configuracao_conta(usuario)
    for field, value in dados.items():
        if hasattr(config, field):
            setattr(config, field, value)
    config.save()
    cache.set(CACHE_KEY.format(id=usuario.id), config)
    return config


def get_autorizacao_rede_url(rede: str) -> str:
    """Retorna URL de autorização para conectar uma rede social."""
    urls = {
        "github": "https://github.com/login/oauth/authorize",
    }
    return urls.get(rede, "/")
