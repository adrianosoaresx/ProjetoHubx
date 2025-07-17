
import uuid
from django.db import models
from django.conf import settings
from model_utils.models import TimeStampedModel


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
        default=uuid.uuid4().hex
    )
    tipo_destino = models.CharField(
        max_length=20,
        choices=TipoUsuario.choices
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.NOVO
    )
    data_expiracao = models.DateTimeField()

    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens_gerados"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="token_usado"
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="tokens"
    )
    nucleos = models.ManyToManyField(
        "nucleos.Nucleo",
        related_name="tokens",
        blank=True
    )

    class Meta:
        verbose_name = "Token de Acesso"
        verbose_name_plural = "Tokens de Acesso"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.codigo} -> {self.get_tipo_destino_display()}"
