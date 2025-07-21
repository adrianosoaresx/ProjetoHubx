from django.db import models
from django.conf import settings
from model_utils.models import TimeStampedModel


class ConfiguracaoConta(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracao",
    )
    receber_notificacoes_email = models.BooleanField(default=True)
    receber_notificacoes_whatsapp = models.BooleanField(default=False)
    tema_escuro = models.BooleanField(default=False)

    class Meta:
        ordering = ["-modified"]
