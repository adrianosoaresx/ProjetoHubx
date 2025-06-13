from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import NotificationSettings

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """Cria as configuracoes de notificacao padrao para novos usuarios."""
    if created:
        NotificationSettings.objects.create(user=instance)
