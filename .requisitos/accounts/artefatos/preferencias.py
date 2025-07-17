from django.db import models
from django.conf import settings

class ConfiguracaoConta(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracoes"
    )
    receber_notificacoes_email = models.BooleanField(default=True)
    receber_notificacoes_whatsapp = models.BooleanField(default=False)
    tema_escuro = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferências de {self.user}"
