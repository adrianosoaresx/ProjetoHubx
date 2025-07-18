import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel
import pyotp


class TokenAcesso(TimeStampedModel):
    class TipoUsuario(models.TextChoices):
        ADMIN = "admin", "Admin"
        ASSOCIADO = "associado", "Associado"
        NUCLEADO = "nucleado", "Nucleado"
        COORDENADOR = "coordenador", "Coordenador"
        CONVIDADO = "convidado", "Convidado"

    class Estado(models.TextChoices):
        NOVO = "novo", "Não usado"
        USADO = "usado", "Usado"
        EXPIRADO = "expirado", "Expirado"

    codigo = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        default=uuid.uuid4().hex,
    )
    tipo_destino = models.CharField(
        max_length=20, choices=TipoUsuario.choices
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.NOVO,
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
        null=True,
        blank=True,
        related_name="token_usado",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao", on_delete=models.CASCADE
    )
    nucleos = models.ManyToManyField(
        "nucleos.Nucleo",
        blank=True,
    )

    class Meta:
        ordering = ["-created"]


class CodigoAutenticacao(TimeStampedModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="codigos_autenticacao"
    )
    codigo = models.CharField(max_length=8, editable=False)
    expira_em = models.DateTimeField()
    verificado = models.BooleanField(default=False)
    tentativas = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex[:8]
        if not self.expira_em:
            self.expira_em = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expirado(self) -> bool:
        return timezone.now() > self.expira_em


class TOTPDevice(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    secret = models.CharField(max_length=32)
    confirmado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    def gerar_totp(self) -> str:
        totp = pyotp.TOTP(self.secret)
        return totp.now()
