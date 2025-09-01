from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import bump_cache_version

from .models import Organizacao


@receiver([post_save, post_delete], sender=Organizacao)
def invalidate_organizacao_list_cache(**_kwargs) -> None:
    """Limpa cache da listagem de organizações após alterações."""
    bump_cache_version("organizacoes_list")
