from django.db import models
from django.conf import settings
from model_utils.models import TimeStampedModel

class ConfiguracaoConta(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracao"
    )
    idioma = models.CharField(
        max_length=10,
        choices=[("pt-br", "Português"), ("en-us", "English")],
        default="pt-br"
    )
    tema = models.CharField(
        max_length=10,
        choices=[("light", "Claro"), ("dark", "Escuro")],
        default="light"
    )
    timezone = models.CharField(
        max_length=50,
        default="America/Sao_Paulo"
    )
    notificacoes_email = models.BooleanField(default=True)
    notificacoes_push = models.BooleanField(default=True)
    privacidade_perfil = models.CharField(
        max_length=10,
        choices=[("publico", "Público"), ("associados", "Associados"), ("privado", "Privado")],
        default="publico"
    )

    class Meta:
        ordering = ["-modified"]
