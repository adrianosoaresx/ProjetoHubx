# accounts/models.py
from __future__ import annotations

import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import PROTECT, SET_NULL
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from core.fields import URLField
from core.models import TimeStampedModel

# ───────────────────────────────────────────────────────────────
#  Validador de CPF simples (###.###.###-## ou ###########)
cpf_validator = RegexValidator(
    regex=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$",
    message="Digite um CPF válido no formato 000.000.000-00.",
)


def generate_secure_token() -> str:
    """Retorna um token seguro com entropia >= 128 bits."""
    return secrets.token_urlsafe(32)


class UserQuerySet(models.QuerySet):
    def filter_current_org(self, org):
        return self.filter(organization=org)


class UserType(models.TextChoices):
    ROOT = "root", "Root"
    ADMIN = "admin", "Admin"
    COORDENADOR = "coordenador", "Coordenador"
    NUCLEADO = "nucleado", "Nucleado"
    ASSOCIADO = "associado", "Associado"
    CONVIDADO = "convidado", "Convidado"


class CustomUserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    """User manager que utiliza o email como identificador principal."""

    def _create_user(self, email: str, username: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        user_type: UserType = UserType.CONVIDADO,
        **extra_fields,
    ):
        extra_fields.setdefault("user_type", user_type.value)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email: str, username: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", UserType.ROOT.value)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, username, password, **extra_fields)

    def get_by_natural_key(self, email: str):
        return self.get(email__iexact=email)


class User(AbstractUser, TimeStampedModel):
    """
    Modelo de usuário customizado.
    Herdamos de AbstractUser para manter toda a infraestrutura
    (senha, permissões, is_staff, etc.) e apenas adicionamos campos extras.
    """

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=False,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )

    email = models.EmailField(
        _("email address"),
        unique=True,
        blank=False,
        null=False,
        db_index=True,
    )

    # Campos adicionais
    phone_number = PhoneNumberField(
        "Telefone",
        region="BR",
        blank=True,
        null=True,
        help_text="Ex.: +55 48 99999-0000",
    )
    address = models.CharField(
        "Endereço",
        max_length=255,
        blank=True,
        help_text="Rua, número, complemento, cidade/UF",
    )
    birth_date = models.DateField("Data de nascimento", blank=True, null=True)
    cpf = models.CharField(
        "CPF",
        max_length=14,  # 000.000.000-00
        blank=True,
        null=True,
        unique=True,
        validators=[cpf_validator],
    )
    nome_completo = models.CharField(max_length=255, blank=True)
    biografia = models.TextField(blank=True)
    cover = models.ImageField(upload_to="users/capas/", null=True, blank=True)
    fone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)

    # Campos migrados do antigo modelo Perfil
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=10, blank=True)
    facebook = URLField(blank=True)
    twitter = URLField(blank=True)
    instagram = URLField(blank=True)
    linkedin = URLField(blank=True)
    website = URLField(blank=True)
    redes_sociais = models.JSONField(default=dict, blank=True, null=True)
    idioma = models.CharField(max_length=10, blank=True)
    fuso_horario = models.CharField(max_length=50, blank=True)
    perfil_publico = models.BooleanField(default=True)
    mostrar_email = models.BooleanField(default=True)
    mostrar_telefone = models.BooleanField(default=False)

    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    lock_expires_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    exclusao_confirmada = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.CONVIDADO,
        verbose_name="Tipo de Usuário",
    )

    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=PROTECT,
        related_name="users",
        null=True,  # Alterado de False para True
        blank=True,  # Permitir valores nulos
        default=None,  # Removido o valor padrão inválido
        verbose_name=_("Organização"),
    )
    is_associado = models.BooleanField(default=False, verbose_name=_("É associado"))
    is_coordenador = models.BooleanField(default=False, verbose_name=_("É coordenador"))
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=SET_NULL,
        related_name="usuarios_principais",
        null=True,
        blank=True,
        verbose_name=_("Núcleo"),
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    @property
    def organizacao_display(self):
        return self.organizacao

    @organizacao_display.setter
    def organizacao_display(self, value):
        self.organizacao = value

    @property
    def get_tipo_usuario(self):
        if self.is_superuser:
            return UserType.ROOT.value
        if self.is_staff and not self.is_associado:
            return UserType.ADMIN.value
        if self.is_associado and self.nucleo and self.is_coordenador:
            return UserType.COORDENADOR.value
        if self.is_associado and self.nucleo and not self.is_coordenador:
            return UserType.NUCLEADO.value
        if self.is_associado and not self.nucleo:
            return UserType.ASSOCIADO.value
        return UserType.CONVIDADO.value

    def save(self, *args, **kwargs):
        if self.user_type == UserType.ROOT.value:
            self.nucleo = None  # Garantir que usuários root não interajam com núcleos
        super().save(*args, **kwargs)

    # Relacionamentos sociais
    connections = models.ManyToManyField("self", blank=True)
    followers = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="following",
        blank=True,
    )

    # Configurações de metadados
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        # Removida a constraint temporariamente para evitar erro
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=["username", "organizacao"],
        #         name="accounts_user_username_org_uniq",
        #     )
        # ]

    # Representação legível
    def __str__(self):
        return self.get_full_name() or self.username


class NotificationSettings(TimeStampedModel):
    """Preferências de notificação do usuário."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    email_conexoes = models.BooleanField(default=True)
    email_mensagens = models.BooleanField(default=True)
    email_eventos = models.BooleanField(default=True)
    email_newsletter = models.BooleanField(default=True)
    sistema_conexoes = models.BooleanField(default=True)
    sistema_mensagens = models.BooleanField(default=True)
    sistema_eventos = models.BooleanField(default=True)
    sistema_comentarios = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuração de Notificação"
        verbose_name_plural = "Configurações de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"Notificações de {self.user}"


class MediaTag(TimeStampedModel):
    """Tags para categorizar mídias dos usuários."""

    nome = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Tag de Mídia"
        verbose_name_plural = "Tags de Mídia"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class UserMedia(TimeStampedModel):
    """Arquivos de mídia (imagens, vídeos, PDFs) enviados pelo usuário."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medias",
    )
    file = models.FileField(upload_to="user_media/")
    descricao = models.CharField("Descrição", max_length=255, blank=True)
    tags = models.ManyToManyField(MediaTag, related_name="medias", blank=True)

    class Meta:
        verbose_name = "Mídia do Usuário"
        verbose_name_plural = "Mídias do Usuário"

    def clean(self) -> None:
        """Valida o tamanho e a extensão do arquivo enviado."""
        super().clean()
        if self.file:
            ext = Path(self.file.name).suffix.lower()
            allowed = getattr(settings, "USER_MEDIA_ALLOWED_EXTS", [])
            if ext not in allowed:
                raise ValidationError({"file": _("Formato de arquivo não suportado.")})
            max_size = getattr(settings, "USER_MEDIA_MAX_SIZE", 50 * 1024 * 1024)
            if self.file.size > max_size:
                raise ValidationError(
                    {"file": _("Arquivo maior que %(size)d MB.") % {"size": max_size // (1024 * 1024)}}
                )

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.user.username} - {self.file.name}"


class AccountToken(TimeStampedModel):
    class Tipo(models.TextChoices):
        EMAIL_CONFIRMATION = "email_confirmation", "Confirmação de Email"
        PASSWORD_RESET = "password_reset", "Redefinição de Senha"

    codigo = models.CharField(max_length=64, unique=True, default=generate_secure_token)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_tokens")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_gerado = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Token de Conta"
        verbose_name_plural = "Tokens de Conta"


class LoginAttempt(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    sucesso = models.BooleanField(default=False)
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tentativa de Login"
        verbose_name_plural = "Tentativas de Login"


class SecurityEvent(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_events",
    )
    evento = models.CharField(max_length=50)
    ip = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de Segurança"
        verbose_name_plural = "Eventos de Segurança"
