from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Comment, Like, Post
from .tasks import notificar_autor_sobre_interacao


@receiver(post_save, sender=Like)
def notificar_like(sender, instance, created, **kwargs):
    if created:
        try:
            enviar_para_usuario(instance.post.autor, "feed_like", {"post_id": str(instance.post.id)})
        except Exception:  # pragma: no cover - melhor esforço
            pass
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notificar_autor_sobre_interacao(instance.post_id, "like")
        else:
            notificar_autor_sobre_interacao.delay(instance.post_id, "like")


@receiver(post_save, sender=Comment)
def notificar_comment(sender, instance, created, **kwargs):
    if created:
        try:
            enviar_para_usuario(instance.post.autor, "feed_comment", {"post_id": str(instance.post.id)})
        except Exception:  # pragma: no cover - melhor esforço
            pass
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            notificar_autor_sobre_interacao(instance.post_id, "comment")
        else:
            notificar_autor_sobre_interacao.delay(instance.post_id, "comment")


@receiver([post_save, post_delete], sender=Post)
def limpar_cache_feed(**_kwargs) -> None:
    """Remove entradas de cache após alterações em posts."""
    cache.clear()
