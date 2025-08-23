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
CONTEXT_CACHE_KEY = "config_context:{user_id}:{escopo_tipo}:{escopo_id}"
_CACHE_MISS = object()


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
    key = CONTEXT_CACHE_KEY.format(
        user_id=usuario.id, escopo_tipo=escopo_tipo, escopo_id=escopo_id
    )
    config = cache.get(key, _CACHE_MISS)
    if config is _CACHE_MISS:
        try:
            config = ConfiguracaoContextual.objects.get(
                user=usuario, escopo_tipo=escopo_tipo, escopo_id=escopo_id
            )
        except ConfiguracaoContextual.DoesNotExist:
            config = None
        cache.set(key, config)
    return config


def merge_preferences(
    global_prefs: ConfiguracaoConta,
    contextual: ConfiguracaoContextual | None,
) -> ConfiguracaoConta:
    """Mescla preferências globais com contextuais."""
    prefs = deepcopy(global_prefs)
    if contextual is None:
        return prefs
    for field in [
        "receber_notificacoes_email",
        "frequencia_notificacoes_email",
        "receber_notificacoes_whatsapp",
        "frequencia_notificacoes_whatsapp",
        "receber_notificacoes_push",
        "frequencia_notificacoes_push",
        "idioma",
        "tema",
    ]:
        value = getattr(contextual, field)
        if value is not None:
            setattr(prefs, field, value)
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


def get_autorizacao_rede_url(rede: str) -> str:
    """Retorna URL de autorização para conectar uma rede social."""
    urls = {
        "github": "https://github.com/login/oauth/authorize",
    }
    return urls.get(rede, "/")
