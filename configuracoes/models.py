from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

NOTIFICACAO_FREQ_CHOICES = [
    ("imediata", "Imediata"),
    ("diaria", "Diária"),
    ("semanal", "Semanal"),
]

IDIOMA_CHOICES = [
    ("pt-BR", "Português"),
    ("en-US", "English"),
    ("es-ES", "Español"),
]

TEMA_CHOICES = [
    ("claro", "Claro"),
    ("escuro", "Escuro"),
    ("automatico", "Automático"),
]


class ConfiguracaoConta(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracao",
    )
    receber_notificacoes_email = models.BooleanField(default=True)
    frequencia_notificacoes_email = models.CharField(
        max_length=8,
        choices=NOTIFICACAO_FREQ_CHOICES,
        default="imediata",
    )
    receber_notificacoes_whatsapp = models.BooleanField(default=False)
    frequencia_notificacoes_whatsapp = models.CharField(
        max_length=8,
        choices=NOTIFICACAO_FREQ_CHOICES,
        default="imediata",
    )
    idioma = models.CharField(max_length=5, choices=IDIOMA_CHOICES, default="pt-BR")
    tema = models.CharField(max_length=10, choices=TEMA_CHOICES, default="claro")
    tema_escuro = models.BooleanField(default=False, help_text="Obsoleto; use 'tema'")

    class Meta:
        ordering = ["-modified"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"], name="configuracao_conta_user_unique"
            )
        ]
