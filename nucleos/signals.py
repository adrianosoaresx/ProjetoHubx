from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import bump_cache_version

from .models import CoordenadorSuplente, ParticipacaoNucleo


@receiver([post_save, post_delete], sender=ParticipacaoNucleo)
def invalidate_participacao(sender, instance, **kwargs):
    nucleo_id = instance.nucleo_id
    org_id = instance.nucleo.organizacao_id
    bump_cache_version("nucleos_list")
    bump_cache_version("nucleos_meus")
    bump_cache_version(f"nucleo_{nucleo_id}_membros")
    bump_cache_version(f"nucleo_{nucleo_id}_metrics")
    bump_cache_version(f"nucleos_list_{org_id}")
@receiver([post_save, post_delete], sender=CoordenadorSuplente)
def invalidate_suplente(sender, instance, **kwargs):
    nucleo_id = instance.nucleo_id
    org_id = instance.nucleo.organizacao_id
    bump_cache_version("nucleos_list")
    bump_cache_version("nucleos_meus")
    bump_cache_version(f"nucleo_{nucleo_id}_membros")
    bump_cache_version(f"nucleo_{nucleo_id}_metrics")
    bump_cache_version(f"nucleos_list_{org_id}")
