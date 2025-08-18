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


def merge_preferences(
    global_prefs: ConfiguracaoConta,
    contextual: ConfiguracaoContextual | None,
) -> ConfiguracaoConta:
    """Mescla preferências globais com contextuais."""
    prefs = deepcopy(global_prefs)
    if contextual is None:
        return prefs
    for field in [
        "frequencia_notificacoes_email",
        "frequencia_notificacoes_whatsapp",
        "receber_notificacoes_push",
        "frequencia_notificacoes_push",
        "idioma",
        "tema",
    ]:
        setattr(prefs, field, getattr(contextual, field))
    return prefs


def get_user_preferences(
    usuario: User, escopo_tipo: str | None = None, escopo_id: str | None = None
) -> ConfiguracaoConta:
    """Resolve preferências do usuário considerando escopo contextual."""
    base = get_configuracao_conta(usuario)
    if escopo_tipo and escopo_id:
        ctx = get_configuracao_contextual(usuario, escopo_tipo, escopo_id)
        return merge_preferences(base, ctx)
    return deepcopy(base)


def atualizar_preferencias_usuario(usuario: User, dados: dict[str, Any]) -> ConfiguracaoConta:
    """Atualiza as preferências do usuário e invalida o cache."""
    config = get_configuracao_conta(usuario)
    for field, value in dados.items():
        if hasattr(config, field):
            setattr(config, field, value)
    config.save()
    cache.set(CACHE_KEY.format(id=usuario.id), config)
    return config
