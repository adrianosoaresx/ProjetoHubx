from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

import sentry_sdk
from django.core.cache import cache

from accounts.models import User

from . import metrics
from .models import ConfiguracaoConta, ConfiguracaoContextual

CACHE_KEY = "configuracao_conta:{id}"
PREFS_CACHE_KEY = "user_prefs:{id}:{tipo}:{escopo}"


def get_configuracao_conta(usuario: User) -> ConfiguracaoConta:
    """Obtém configurações do cache ou do banco com chave única por usuário."""
    start = time.monotonic()
    key = CACHE_KEY.format(id=usuario.id)
    config = cache.get(key)
    if config is None:
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


def get_configuracao_contextual(
    usuario: User, escopo_tipo: str, escopo_id: str
) -> ConfiguracaoContextual | None:
    """Retorna configurações específicas de um escopo, se existirem."""
    try:
        return ConfiguracaoContextual.objects.get(
            user=usuario, escopo_tipo=escopo_tipo, escopo_id=escopo_id
        )
    except ConfiguracaoContextual.DoesNotExist:
        return None


def get_user_preferences(
    usuario: User, escopo_tipo: str | None = None, escopo_id: str | None = None
) -> ConfiguracaoConta:
    """Resolve preferências do usuário considerando escopo contextual.

    Resultado é cacheado por usuário+escopo para garantir leitura rápida
    (p95 ≤ 100ms) e exposto em métricas de hits/misses/latência.
    """

    start = time.monotonic()
    key = PREFS_CACHE_KEY.format(
        id=usuario.id,
        tipo=escopo_tipo or "global",
        escopo=escopo_id or "global",
    )
    prefs = cache.get(key)
    if prefs is not None:
        metrics.config_cache_hits_total.inc()
        metrics.config_get_latency_seconds.observe(time.monotonic() - start)
        return deepcopy(prefs)

    metrics.config_cache_misses_total.inc()
    prefs = deepcopy(get_configuracao_conta(usuario))
    if escopo_tipo and escopo_id:
        ctx = get_configuracao_contextual(usuario, escopo_tipo, escopo_id)
        if ctx:
            prefs.frequencia_notificacoes_email = ctx.frequencia_notificacoes_email
            prefs.frequencia_notificacoes_whatsapp = (
                ctx.frequencia_notificacoes_whatsapp
            )
            prefs.idioma = ctx.idioma
            prefs.tema = ctx.tema
    cache.set(key, prefs)
    metrics.config_get_latency_seconds.observe(time.monotonic() - start)
    return deepcopy(prefs)


def atualizar_preferencias_usuario(usuario: User, dados: dict[str, Any]) -> ConfiguracaoConta:
    """Atualiza as preferências do usuário e invalida o cache."""
    config = get_configuracao_conta(usuario)
    for field, value in dados.items():
        if hasattr(config, field):
            setattr(config, field, value)
    config.save()
    cache.set(CACHE_KEY.format(id=usuario.id), config)
    try:
        cache.delete_pattern(f"user_prefs:{usuario.id}:*")
    except AttributeError:  # pragma: no cover - backend sem suporte
        cache.clear()
    return config
