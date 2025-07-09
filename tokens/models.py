from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
import uuid

from core.models import TimeStampedModel


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
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField()
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens_gerados",
    )
    nucleo_destino = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tokens",
    )

    class Meta:
        verbose_name = "Token de Acesso"
        verbose_name_plural = "Tokens de Acesso"
        managed = False
        db_table = "accounts_tokenacesso"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.codigo
