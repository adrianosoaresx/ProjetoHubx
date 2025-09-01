from __future__ import annotations

"""Rate limiting utilities for tokens app."""

import time
from dataclasses import dataclass

from django.conf import settings
from django_redis import get_redis_connection
from django.core.cache import cache


@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: int


DEFAULT_LIMITS = {"burst": (10, 60), "sustained": (100, 3600)}


def check_rate_limit(key: str) -> RateLimitResult:
    """Incrementa contadores de rate limit e retorna resultado.

    Usa política configurada em ``settings.TOKENS_RATE_LIMITS``.
    """

    if not getattr(settings, "TOKENS_RATE_LIMIT_ENABLED", True):
        return RateLimitResult(True, 0)

    limits = getattr(settings, "TOKENS_RATE_LIMITS", DEFAULT_LIMITS)
    try:
        conn = get_redis_connection("default")
        use_cache = False
    except Exception:
        conn = cache
        use_cache = True
    now = int(time.time())
    allowed = True
    retry_after = 0
    for limit, period in limits.values():
        redis_key = f"tokens:rl:{key}:{period}"
        if use_cache:
            count = conn.get(redis_key, 0) + 1
            conn.set(redis_key, count, timeout=period)
            ttl = period
        else:
            count = conn.incr(redis_key)
            if count == 1:
                conn.expire(redis_key, period)
            ttl = conn.ttl(redis_key)
        if count > limit:
            allowed = False
            retry_after = max(retry_after, ttl)
    return RateLimitResult(allowed, retry_after)
