from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from notificacoes.services.notificacoes import enviar_para_usuario

from .models import Comment, Like


@receiver(post_save, sender=Like)
def notificar_like(sender, instance, created, **kwargs):
    if created:
        try:
            enviar_para_usuario(instance.post.autor, "feed_like", {"post_id": str(instance.post.id)})
        except Exception:
            pass


@receiver(post_save, sender=Comment)
def notificar_comment(sender, instance, created, **kwargs):
    if created:
        try:
            enviar_para_usuario(instance.post.autor, "feed_comment", {"post_id": str(instance.post.id)})
        except Exception:
            pass
