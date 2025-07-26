from __future__ import annotations

import random
import uuid

import pyotp
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.fields import EncryptedCharField
from core.models import TimeStampedModel


def generate_hex_uuid() -> str:
    return uuid.uuid4().hex


class TokenAcesso(TimeStampedModel):
    class TipoUsuario(models.TextChoices):
        ADMIN = "admin", "Admin"
        ASSOCIADO = "associado", "Associado"
        NUCLEADO = "nucleado", "Nucleado"
        COORDENADOR = "coordenador", "Coordenador"
        CONVIDADO = "convidado", "Convidado"

    class Estado(models.TextChoices):
        NOVO = "novo", _("Não usado")
        USADO = "usado", _("Usado")
        EXPIRADO = "expirado", _("Expirado")
        REVOGADO = "revogado", _("Revogado")

    codigo = models.CharField(
        max_length=32,
        default=generate_hex_uuid,
        unique=True,
        editable=False,
    )
    tipo_destino = models.CharField(max_length=20, choices=TipoUsuario.choices)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.NOVO,
    )
    data_expiracao = models.DateTimeField(null=True, blank=True)
    ip_gerado = models.GenericIPAddressField(null=True, blank=True)
    ip_utilizado = models.GenericIPAddressField(null=True, blank=True)
    revogado_em = models.DateTimeField(null=True, blank=True)
    revogado_por = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tokens_revogados",
    )

    gerado_por = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="tokens_gerados",
    )
    usuario = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="tokens_recebidos",
        null=True,
        blank=True,
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="tokens",
        null=True,
        blank=True,
    )
    nucleos = models.ManyToManyField(
        "nucleos.Nucleo",
        blank=True,
        related_name="tokens",
    )

    class Meta:
        ordering = ["-created_at"]


class TokenUsoLog(models.Model):
    class Acao(models.TextChoices):
        GERACAO = "geracao", _("Geração")
        VALIDACAO = "validacao", _("Validação")
        USO = "uso", _("Uso")
        REVOGACAO = "revogacao", _("Revogação")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.ForeignKey(
        TokenAcesso,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    usuario = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    acao = models.CharField(max_length=20, choices=Acao.choices)
    ip = EncryptedCharField(max_length=128, null=True, blank=True)
    user_agent = EncryptedCharField(max_length=512, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]


class CodigoAutenticacao(TimeStampedModel):
    usuario = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="codigos_autenticacao",
    )
    codigo = models.CharField(max_length=8)
    expira_em = models.DateTimeField()
    verificado = models.BooleanField(default=False)
    tentativas = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.codigo = f"{random.randint(0, 999999):06d}"
            self.expira_em = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expirado(self) -> bool:
        return timezone.now() > self.expira_em

    class Meta:
        ordering = ["-created_at"]


class TOTPDevice(TimeStampedModel):
    usuario = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret = models.CharField(max_length=32)
    confirmado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = pyotp.random_base32()
        super().save(*args, **kwargs)

    def gerar_totp(self) -> str:
        return pyotp.TOTP(self.secret).now()

    class Meta:
        ordering = ["-created_at"]
