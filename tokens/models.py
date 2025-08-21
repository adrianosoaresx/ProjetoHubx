from __future__ import annotations

import base64
import hashlib
import hmac
import random
import secrets
import uuid

import pyotp
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.fields import EncryptedCharField
from core.models import SoftDeleteModel, TimeStampedModel

User = get_user_model()


class ApiToken(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_tokens",
        null=True,
        blank=True,
    )
    client_name = models.CharField(max_length=100, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scope = models.CharField(
        max_length=20,
        choices=[("read", "Read"), ("write", "Write"), ("admin", "Admin")],
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revogado_por = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="api_tokens_revogados",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and (self.expires_at is None or self.expires_at > timezone.now())

    class Meta:
        ordering = ["-created_at"]


class ApiTokenIp(TimeStampedModel, SoftDeleteModel):
    class Tipo(models.TextChoices):
        PERMITIDO = "permitido", _("Permitido")
        NEGADO = "negado", _("Negado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.ForeignKey(
        ApiToken,
        on_delete=models.CASCADE,
        related_name="ips",
    )
    ip = models.GenericIPAddressField()
    tipo = models.CharField(max_length=10, choices=Tipo.choices)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("token", "ip", "tipo")


class ApiTokenLog(TimeStampedModel, SoftDeleteModel):
    class Acao(models.TextChoices):
        GERACAO = "geracao", _("Geração")
        USO = "uso", _("Uso")
        REVOGACAO = "revogacao", _("Revogação")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.ForeignKey(
        ApiToken,
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

    class Meta:
        ordering = ["-created_at"]


def generate_hex_uuid() -> str:
    return uuid.uuid4().hex


class TokenAcesso(TimeStampedModel, SoftDeleteModel):
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

    codigo_hash = models.CharField(max_length=64, unique=True)
    codigo_salt = models.CharField(max_length=32)
    tipo_destino = models.CharField(max_length=20, choices=TipoUsuario.choices)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.NOVO,
    )
    data_expiracao = models.DateTimeField(null=True, blank=True)
    ip_gerado = models.CharField(max_length=45, null=True, blank=True)
    ip_utilizado = models.CharField(max_length=45, null=True, blank=True)
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

    # o código não é persistido em texto claro
    _codigo: str | None = None

    @property
    def codigo(self) -> str | None:
        return self._codigo

    @codigo.setter
    def codigo(self, value: str) -> None:
        self._codigo = value

    @staticmethod
    def generate_code() -> str:
        """Gera um código aleatório com entropia >= 128 bits."""
        return secrets.token_urlsafe(32)

    def set_codigo(self, codigo: str) -> None:
        """Define ``codigo`` gerando hash para persistência."""
        # Tokens gerados após a introdução deste método utilizam SHA256
        # simples para permitir busca direta pelo hash.
        self.codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
        # ``codigo_salt`` permanece para compatibilidade com tokens antigos
        # que ainda utilizam PBKDF2 com salt.
        self.codigo_salt = ""

    def check_codigo(self, codigo: str) -> bool:
        """Verifica o ``codigo`` considerando tokens legados."""
        if self.codigo_salt:
            # Compatibilidade com tokens gerados antes da mudança,
            # que utilizam PBKDF2 com salt.
            salt = base64.b64decode(self.codigo_salt)
            expected = base64.b64decode(self.codigo_hash)
            digest = hashlib.pbkdf2_hmac("sha256", codigo.encode(), salt, 120000)
            return hmac.compare_digest(expected, digest)
        # Tokens novos armazenam apenas o SHA256 do código.
        return self.codigo_hash == hashlib.sha256(codigo.encode()).hexdigest()


class TokenUsoLog(TimeStampedModel, SoftDeleteModel):
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

    class Meta:
        ordering = ["-created_at"]


class CodigoAutenticacao(TimeStampedModel, SoftDeleteModel):
    usuario = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="codigos_autenticacao",
    )
    codigo_hash = models.CharField(max_length=64)
    codigo_salt = models.CharField(max_length=32)
    expira_em = models.DateTimeField()
    verificado = models.BooleanField(default=False)
    tentativas = models.PositiveSmallIntegerField(default=0)

    _codigo: str | None = None

    @property
    def codigo(self) -> str | None:
        return self._codigo

    @codigo.setter
    def codigo(self, value: str) -> None:
        self._codigo = value

    def set_codigo(self, codigo: str) -> None:
        self._codigo = codigo
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", codigo.encode(), salt, 120000)
        self.codigo_salt = base64.b64encode(salt).decode()
        self.codigo_hash = base64.b64encode(digest).decode()

    def check_codigo(self, codigo: str) -> bool:
        salt = base64.b64decode(self.codigo_salt)
        expected = base64.b64decode(self.codigo_hash)
        digest = hashlib.pbkdf2_hmac("sha256", codigo.encode(), salt, 120000)
        return hmac.compare_digest(expected, digest)

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self._codigo:
                self._codigo = f"{random.randint(0, 999999):06d}"
            self.set_codigo(self._codigo)
            self.expira_em = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expirado(self) -> bool:
        return timezone.now() > self.expira_em

    class Meta:
        ordering = ["-created_at"]


class CodigoAutenticacaoLog(TimeStampedModel, SoftDeleteModel):
    class Acao(models.TextChoices):
        EMISSAO = "emissao", _("Emissão")
        VALIDACAO = "validacao", _("Validação")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.ForeignKey(
        CodigoAutenticacao,
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

    class Meta:
        ordering = ["-created_at"]


class TOTPDevice(TimeStampedModel, SoftDeleteModel):
    usuario = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret = EncryptedCharField(max_length=128)
    confirmado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = pyotp.random_base32()
        super().save(*args, **kwargs)

    def gerar_totp(self) -> str:
        return pyotp.TOTP(self.secret).now()

    class Meta:
        ordering = ["-created_at"]
