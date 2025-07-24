# accounts/models.py
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import PROTECT
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel

# ───────────────────────────────────────────────────────────────
#  Validador de CPF simples (###.###.###-## ou ###########)
cpf_validator = RegexValidator(
    regex=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$",
    message="Digite um CPF válido no formato 000.000.000-00.",
)


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
        **extra_fields,
    ):
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email: str, username: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
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

    # Campos adicionais conforme requisitos
    nome_completo = models.CharField(max_length=150, blank=True)
    cpf = models.CharField(max_length=14, unique=True, validators=[cpf_validator], blank=True, null=True)
    avatar = models.ImageField(upload_to="usuarios/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="usuarios/capas/", blank=True, null=True)
    biografia = models.TextField(blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=9, blank=True)
    fone = models.CharField(max_length=15, blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)
    redes_sociais = models.JSONField(blank=True, null=True)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    is_associado = models.BooleanField(default=False)
    nucleos = models.ManyToManyField(
        "nucleos.Nucleo",
        through="nucleos.ParticipacaoNucleo",
        related_name="usuarios",
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

    def get_tipo_usuario(self) -> str:
        if self.is_superuser:
            return UserType.ROOT.value
        if self.is_staff and not self.is_associado:
            return UserType.ADMIN.value
        if self.participacoes.filter(is_coordenador=True).exists():
            return UserType.COORDENADOR.value
        if self.is_associado and self.nucleos.exists():
            return UserType.NUCLEADO.value
        if self.is_associado:
            return UserType.ASSOCIADO.value
        return UserType.CONVIDADO.value

    def is_coordenador_do(self, nucleo) -> bool:
        return self.participacoes.filter(nucleo=nucleo, is_coordenador=True).exists()

    def save(self, *args, **kwargs):
        if not self.is_superuser and not self.organizacao:
            raise ValidationError({"organizacao": "Obrigatória para usuários comuns."})
        super().save(*args, **kwargs)

    # Relacionamentos sociais
    connections = models.ManyToManyField("self", blank=True)
    followers = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="following",
        blank=True,
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    # Representação legível
    def __str__(self):
        return self.get_full_name() or self.username


class ConfiguracaoDeConta(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configuracoes",
    )
    receber_notificacoes_email = models.BooleanField(default=True)
    receber_notificacoes_whatsapp = models.BooleanField(default=False)
    tema_escuro = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuração de Conta"
        verbose_name_plural = "Configurações de Conta"

    def __str__(self) -> str:
        return f"Configuração de {self.user}"


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

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.user.username} - {self.file.name}"


@receiver(post_save, sender=User)
def criar_configuracao_conta(sender, instance: User, created: bool, **_: object) -> None:
    if created:
        ConfiguracaoDeConta.objects.create(user=instance)
