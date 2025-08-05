from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from notificacoes.models import UserNotificationPreference

from .models import ConfiguracaoConta


@receiver(post_save, sender=ConfiguracaoConta)
def sync_preferences(sender, instance, **kwargs) -> None:
    UserNotificationPreference.objects.update_or_create(
        user=instance.user,
        defaults={
            "email": instance.receber_notificacoes_email,
            "whatsapp": instance.receber_notificacoes_whatsapp,
            "frequencia_email": instance.frequencia_notificacoes_email,
            "frequencia_whatsapp": instance.frequencia_notificacoes_whatsapp,
        },
    )
