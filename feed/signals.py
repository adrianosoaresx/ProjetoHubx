from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import bump_cache_version

from .models import Comment, Post, Reacao
from .tasks import notificar_autor_sobre_interacao


@receiver(post_save, sender=Reacao)
def notificar_reacao(sender, instance, created, update_fields=None, **kwargs):
    if created or (update_fields and "deleted" in update_fields and not instance.deleted):
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notificar_autor_sobre_interacao(instance.post_id, instance.vote)
        else:
            notificar_autor_sobre_interacao.delay(instance.post_id, instance.vote)


@receiver(post_save, sender=Comment)
def notificar_comment(sender, instance, created, **kwargs):
    if created:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notificar_autor_sobre_interacao(instance.post_id, "comment")
        else:
            notificar_autor_sobre_interacao.delay(instance.post_id, "comment")


@receiver([post_save, post_delete], sender=Post)
def limpar_cache_feed(**_kwargs) -> None:
    """Atualiza a versão do cache do feed após alterações em posts."""
    bump_cache_version("feed_list")
