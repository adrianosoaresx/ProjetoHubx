from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from configuracoes.models import ConfiguracaoConta

User = get_user_model()


@receiver(post_save, sender=User)
def create_configuracao_conta(sender, instance, created, **kwargs):
    """Cria configuração padrão para novos usuários."""
    if not created:
        return

    ConfiguracaoConta.objects.create(user=instance)
    if instance.user_type in {"root", "admin"}:
        instance.is_staff = True
        instance.save(update_fields=["is_staff"])
