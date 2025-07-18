from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import NotificationSettings
from accounts.models import UserType  # Corrigido o caminho da importação

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """Cria as configuracoes de notificacao padrao para novos usuarios."""
    if created:
        NotificationSettings.objects.create(user=instance)
        tipo_superadmin = UserType.objects.filter(descricao="SUPERADMIN").first()
        tipo_admin = UserType.objects.filter(descricao="ADMIN").first()
        if instance.tipo in {tipo_superadmin, tipo_admin}:
            instance.is_staff = True
            instance.save(update_fields=["is_staff"])
