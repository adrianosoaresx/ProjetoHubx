from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from configuracoes.models import ConfiguracaoConta

from .models import NotificationSettings

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """Cria configuracoes padrao para novos usuarios."""
    if not created:
        return

    NotificationSettings.objects.create(user=instance)
    ConfiguracaoConta.objects.create(user=instance)
    if instance.user_type in {"root", "admin"}:
        instance.is_staff = True
        instance.save(update_fields=["is_staff"])
