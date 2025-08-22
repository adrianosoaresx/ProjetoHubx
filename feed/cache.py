from __future__ import annotations

from django.core.cache import cache


def invalidate_feed_cache(prefix: str = "feed:") -> None:
    """Remove cache entries matching the given prefix.

    It attempts to use ``delete_pattern`` if the backend supports it.
    For backends without pattern deletion support (e.g. locmem), it
    iterates over stored keys and deletes those that start with the
    provided prefix.
    """
    pattern = f"{prefix}*"
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)  # type: ignore[attr-defined]
        return
    version = getattr(cache, "version", 1)
    internal_prefix = f":{version}:{prefix}"
    try:
        keys = [
            k.split(f":{version}:", 1)[1]
            for k in getattr(cache, "_cache").keys()
            if isinstance(k, str) and k.startswith(internal_prefix)
        ]
    except AttributeError:
        keys = []
    if keys:
        cache.delete_many(keys)
