from __future__ import annotations

from django.core.cache import cache


def get_cache_version(namespace: str) -> int:
    """Return the current cache version for the given namespace."""
    key = f"cache_version:{namespace}"
    cache.add(key, 1)
    return int(cache.get(key) or 1)


def bump_cache_version(namespace: str) -> None:
    """Increment the cache version for the given namespace."""
    key = f"cache_version:{namespace}"
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 2)
