from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User, ConfiguracaoConta


@receiver(post_save, sender=User)
def criar_configuracao_padrao(sender, instance, created, **kwargs):
    if created and not hasattr(instance, "configuracoes"):
        ConfiguracaoConta.objects.create(user=instance)

def test_configuracao_criada_automaticamente(user_factory):
    user = user_factory()
    assert hasattr(user, "configuracoes")
    assert user.configuracoes.tema_escuro is False
