from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from django.conf import settings
from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Comment, Like
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
