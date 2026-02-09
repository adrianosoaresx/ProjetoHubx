from datetime import time

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.fields import EncryptedCharField
from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel
from organizacoes.models import Organizacao

NOTIFICACAO_FREQ_CHOICES = [
    ("imediata", _("Imediata")),
    ("diaria", _("Diária")),
    ("semanal", _("Semanal")),
]

IDIOMA_CHOICES = [
    ("pt-br", _("Português (Brasil)")),
    ("en", _("English")),
    ("es", _("Español")),
]

TEMA_CHOICES = [
    ("claro", _("Claro")),
    ("escuro", _("Escuro")),
]

DIAS_SEMANA_CHOICES = [
    (0, _("Segunda")),
    (1, _("Terça")),
    (2, _("Quarta")),
    (3, _("Quinta")),
    (4, _("Sexta")),
    (5, _("Sábado")),
    (6, _("Domingo")),
]


class ConfiguracaoConta(TimeStampedModel, SoftDeleteModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracao",
    )
    chat_habilitado = models.BooleanField(default=True)
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
    receber_notificacoes_push = models.BooleanField(default=True)
    frequencia_notificacoes_push = models.CharField(
        max_length=8,
        choices=NOTIFICACAO_FREQ_CHOICES,
        default="imediata",
    )
    idioma = models.CharField(max_length=5, choices=IDIOMA_CHOICES, default="pt-br")
    tema = models.CharField(max_length=10, choices=TEMA_CHOICES, default="claro")
    hora_notificacao_diaria = models.TimeField(
        default=time(8, 0),
        help_text=_("Horário para envio de notificações diárias"),
    )
    hora_notificacao_semanal = models.TimeField(
        default=time(8, 0),
        help_text=_("Horário para envio de notificações semanais"),
    )
    dia_semana_notificacao = models.PositiveSmallIntegerField(
        choices=DIAS_SEMANA_CHOICES,
        default=0,
        help_text=_("Dia da semana para notificações semanais"),
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user"], name="configuracao_conta_user_unique")]


class ConfiguracaoChatOrganizacao(TimeStampedModel, SoftDeleteModel):
    organizacao = models.OneToOneField(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="configuracao_chat",
    )
    chat_habilitado = models.BooleanField(default=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-updated_at"]


class ConfiguracaoContaLog(TimeStampedModel):
    """Registro de alterações nas configurações de conta."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    campo = models.CharField(max_length=50)
    valor_antigo = models.TextField(null=True, blank=True)
    valor_novo = models.TextField(null=True, blank=True)
    # Valores são armazenados criptografados; o texto cifrado ocupa mais espaço
    # que o valor original. Por isso, os limites no banco precisam ser maiores.
    ip = EncryptedCharField(max_length=255, null=True, blank=True)
    user_agent = EncryptedCharField(max_length=2048, null=True, blank=True)
    fonte = models.CharField(
        max_length=10,
        choices=[("UI", "UI"), ("API", "API"), ("import", "import")],
        default="UI",
    )

    class Meta:
        ordering = ["-created_at"]
