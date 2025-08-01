from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django.utils.translation import gettext_lazy as _

from .models import UserNotificationPreference


# Signal para que outros módulos definam templates padrão
definir_template_default = Signal()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_preferencias_apos_usuario(sender, instance, created, **kwargs):
    """Gera preferências padrão ao criar um usuário."""
    if created:
        UserNotificationPreference.objects.get_or_create(user=instance)

