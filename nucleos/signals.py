from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CoordenadorSuplente, ParticipacaoNucleo


def _delete_pattern(pattern: str) -> None:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
    else:  # pragma: no cover - backend sem suporte
        cache.clear()


@receiver([post_save, post_delete], sender=ParticipacaoNucleo)
def invalidate_participacao(sender, instance, **kwargs):
    nucleo_id = instance.nucleo_id
    org_id = instance.nucleo.organizacao_id
    _delete_pattern(f"nucleo_{nucleo_id}_membros*")
    _delete_pattern(f"nucleo_{nucleo_id}_metrics*")
    _delete_pattern(f"nucleos_list_{org_id}*")
    _delete_pattern(f"org_{org_id}_taxa_participacao")


@receiver([post_save, post_delete], sender=CoordenadorSuplente)
def invalidate_suplente(sender, instance, **kwargs):
    nucleo_id = instance.nucleo_id
    org_id = instance.nucleo.organizacao_id
    _delete_pattern(f"nucleo_{nucleo_id}_membros*")
    _delete_pattern(f"nucleo_{nucleo_id}_metrics*")
    _delete_pattern(f"nucleos_list_{org_id}*")
