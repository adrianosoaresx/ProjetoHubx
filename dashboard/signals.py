from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from agenda.models import InscricaoEvento


@receiver(post_save, sender=InscricaoEvento)
def clear_dashboard_cache(**_kwargs) -> None:
    cache.clear()
