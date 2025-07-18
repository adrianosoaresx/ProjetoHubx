from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel

class UserType(models.TextChoices):
    ROOT = "root", "Root"
    ADMIN = "admin", "Admin"
    ASSOCIADO = "associado", "Associado"
    NUCLEADO = "nucleado", "Nucleado"
    COORDENADOR = "coordenador", "Coordenador"
    CONVIDADO = "convidado", "Convidado"

class UserManager(BaseUserManager):
    def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        user_type: UserType = UserType.CONVIDADO,
        **extra_fields,
    ):
        if not email:
            raise ValueError("O email é obrigatório")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", user_type.value)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, username: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", UserType.ROOT.value)
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    cpf = models.CharField(max_length=11, unique=True)
    telefone = models.CharField(max_length=15)
    avatar = models.ImageField(upload_to="users/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="users/capas/", blank=True, null=True)
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.CASCADE)
    nucleo = models.ForeignKey("nucleos.Nucleo", on_delete=models.SET_NULL, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=10, choices=[("M", "Masculino"), ("F", "Feminino"), ("Outro", "Outro")], blank=True, null=True)
    user_type = models.CharField(
        max_length=20, choices=UserType.choices, default=UserType.CONVIDADO
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo", "cpf", "telefone", "organizacao"]

    class Meta:
        ordering = ["-data_cadastro"]

    def __str__(self):
        return self.email
