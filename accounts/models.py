# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from datetime import timedelta
from django.utils import timezone
import uuid


class UserType(TimeStampedModel):
    """Tipos de usuário cadastrados no sistema."""

    descricao = models.CharField("Descrição", max_length=20)

    class Meta:
        verbose_name = "Tipo de Usuário"
        verbose_name_plural = "Tipos de Usuário"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.descricao


# ───────────────────────────────────────────────────────────────
#  Validador de CPF simples (###.###.###-## ou ###########)
cpf_validator = RegexValidator(
    regex=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$",
    message="Digite um CPF válido no formato 000.000.000-00.",
)


class User(AbstractUser, TimeStampedModel):
    """
    Modelo de usuário customizado.
    Herdamos de AbstractUser para manter toda a infraestrutura
    (senha, permissões, is_staff, etc.) e apenas adicionamos campos extras.
    """

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

    # Campos migrados do antigo modelo Perfil
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    data_nascimento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=1, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=10, blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    website = models.URLField(blank=True)
    idioma = models.CharField(max_length=10, blank=True)
    fuso_horario = models.CharField(max_length=50, blank=True)
    perfil_publico = models.BooleanField(default=True)
    mostrar_email = models.BooleanField(default=True)
    mostrar_telefone = models.BooleanField(default=False)

    class Tipo(models.IntegerChoices):
        SUPERADMIN = 4, _("Root")
        ADMIN = 1, _("Admin")
        GERENTE = 2, _("Manager")
        CLIENTE = 3, _("Client")

    tipo = models.ForeignKey(
        UserType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=Tipo.CLIENTE,
        related_name="users",
    )

    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.SET_NULL,
        related_name="usuarios",
        null=True,
        blank=True,
    )

    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        on_delete=models.SET_NULL,
        related_name="usuarios_principais",
        null=True,
        blank=True,
    )

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
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mídia do Usuário"
        verbose_name_plural = "Mídias do Usuário"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.user.username} - {self.file.name}"


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

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex
        if not self.data_expiracao:
            self.data_expiracao = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.codigo
