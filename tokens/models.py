import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from nucleos.models import Nucleo


class TokenAcesso(TimeStampedModel):
    """Token de convite para cadastro de usuários."""

    class Tipo(models.TextChoices):
        ADMIN = "admin", "admin"
        GERENTE = "gerente", "gerente"
        CLIENTE = "cliente", "cliente"

    class Estado(models.TextChoices):
        NAO_USADO = "novo", "não usado"
        USADO = "usado", "usado"
        EXPIRADO = "expirado", "expirado"

    codigo = models.CharField(max_length=64, unique=True, editable=False)
    tipo_destino = models.CharField(max_length=10, choices=Tipo.choices)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.NAO_USADO
    )
    data_expiracao = models.DateTimeField()
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens_gerados",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens_acesso",
        null=True,
        blank=True,
    )
    nucleos = models.ManyToManyField(
        Nucleo,
        related_name="tokens_acesso",
        blank=True,
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="tokens",
        db_column="organization",
    )

    class Meta:
        verbose_name = "Token de Acesso"
        verbose_name_plural = "Tokens de Acesso"
        db_table = "accounts_tokenacesso"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.codigo
