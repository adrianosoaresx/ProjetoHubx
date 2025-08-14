from __future__ import annotations

from django.db.models.signals import post_migrate
from django.dispatch import Signal, receiver

from .models import NotificationTemplate
from .services import metrics

# Signal para que outros módulos definam templates padrão
definir_template_default = Signal()


@receiver(post_migrate)
def atualizar_templates_total(sender, **kwargs):
    from django.apps import apps

    if apps.is_installed("notificacoes"):
        total = NotificationTemplate.objects.count()
        metrics.templates_total.set(total)
