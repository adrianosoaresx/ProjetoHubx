from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import AccountToken, NotificationSettings
from .tasks import send_confirmation_email

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_settings(sender, instance, created, **kwargs):
    """Cria as configuracoes de notificacao padrao para novos usuarios."""
    if created:
        NotificationSettings.objects.create(user=instance)
        if instance.user_type in {"root", "admin"}:
            instance.is_staff = True
            instance.save(update_fields=["is_staff"])
        if not instance.is_active:
            token = AccountToken.objects.create(
                usuario=instance,
                tipo=AccountToken.Tipo.EMAIL_CONFIRMATION,
                expires_at=timezone.now() + timezone.timedelta(hours=24),
            )
            send_confirmation_email.delay(token.id)
