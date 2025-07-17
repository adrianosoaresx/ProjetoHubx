
from django.db import models
from model_utils.models import TimeStampedModel


class ConfiguracaoConta(TimeStampedModel):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="configuracoes"
    )
    receber_notificacoes_email = models.BooleanField(default=True)
    receber_notificacoes_whatsapp = models.BooleanField(default=False)
    tema_escuro = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuração de Conta"
        verbose_name_plural = "Configurações de Conta"

    def __str__(self):
        return f"Configurações de {self.user.nome_completo}"
