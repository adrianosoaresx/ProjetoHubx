# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import RegexValidator

# ───────────────────────────────────────────────────────────────
#  Validador de CPF simples (###.###.###-## ou ###########)
cpf_validator = RegexValidator(
    regex=r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$",
    message="Digite um CPF válido no formato 000.000.000-00.",
)

class User(AbstractUser):
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
    birth_date = models.DateField(
        "Data de nascimento", blank=True, null=True
    )
    cpf = models.CharField(
        "CPF",
        max_length=14,               # 000.000.000-00
        blank=True,
        unique=True,
        validators=[cpf_validator],
    )

    # …adicione aqui outros campos que existiam em perfil.Profile
    # ex.: avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    # Configurações de metadados
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    # Representação legível
    def __str__(self):
        return self.get_full_name() or self.username
