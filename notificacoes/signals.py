from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_migrate, post_save
from django.dispatch import Signal, receiver

from .models import NotificationTemplate, UserNotificationPreference
from .services import metrics

# Signal para que outros módulos definam templates padrão
definir_template_default = Signal()


User = get_user_model()


def _update_templates_total() -> None:
    """Recalcula e atualiza o gauge de templates ativos."""
    total = NotificationTemplate.objects.filter(ativo=True).count()
    metrics.templates_total.set(total)


@receiver(post_migrate)
def atualizar_templates_total(sender, **kwargs):
    from django.apps import apps

    if apps.is_installed("notificacoes"):
        _update_templates_total()


@receiver(post_save, sender=NotificationTemplate)
def atualizar_templates_total_post_save(sender, **kwargs):
    _update_templates_total()


@receiver(post_delete, sender=NotificationTemplate)
def atualizar_templates_total_post_delete(sender, **kwargs):
    _update_templates_total()


@receiver(post_save, sender=User)
def criar_preferencias_notificacao(sender, instance, created, **kwargs):
    if created:
        UserNotificationPreference.objects.get_or_create(user=instance)
