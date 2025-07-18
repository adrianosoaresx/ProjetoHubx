from django.db.models.signals import post_save
from django.dispatch import receiver
from configuracoes.models import ConfiguracaoConta
from accounts.models import user as User

@receiver(post_save, sender=User)
def criar_configuracao_conta(sender, instance, created, **kwargs):
    if created:
        ConfiguracaoConta.objects.create(user=instance)
