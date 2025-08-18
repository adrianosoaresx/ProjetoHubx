from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate, post_save
from django.dispatch import Signal, receiver

from .models import NotificationTemplate, UserNotificationPreference
from .services import metrics

# Signal para que outros módulos definam templates padrão
definir_template_default = Signal()


User = get_user_model()


@receiver(post_migrate)
def atualizar_templates_total(sender, **kwargs):
    from django.apps import apps

    if apps.is_installed("notificacoes"):
        total = NotificationTemplate.objects.filter(ativo=True).count()
        metrics.templates_total.set(total)


@receiver(post_save, sender=User)
def criar_preferencias_notificacao(sender, instance, created, **kwargs):
    if created:
        UserNotificationPreference.objects.get_or_create(user=instance)
