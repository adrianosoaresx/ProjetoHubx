from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import RespostaDiscussao, TopicoDiscussao


@receiver([post_save, post_delete], sender=TopicoDiscussao)
@receiver([post_save, post_delete], sender=RespostaDiscussao)
def clear_discussao_cache(**_kwargs):
    cache.clear()
