from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from eventos.models import InscricaoEvento


def _invalidate_dashboard_cache(prefix: str) -> None:
    """Remove cache entries matching the given prefix.

    Uses ``delete_pattern`` when available, falling back to manual iteration
    for backends that lack pattern deletion (e.g. locmem).
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


@receiver(post_save, sender=InscricaoEvento)
def clear_dashboard_cache(sender, instance: InscricaoEvento, **_kwargs) -> None:
    """Invalidate cached dashboard metrics for the affected user."""

    prefix = f"dashboard-{instance.user_id}-{instance.user.user_type}-"
    _invalidate_dashboard_cache(prefix)
