from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Organizacao


def _delete_pattern(pattern: str) -> None:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)  # type: ignore[attr-defined]
    else:  # pragma: no cover - backend sem suporte
        cache.clear()


@receiver([post_save, post_delete], sender=Organizacao)
def invalidate_organizacao_list_cache(**_kwargs) -> None:
    """Limpa cache da listagem de organizações após alterações."""
    _delete_pattern("organizacoes_list_*")

