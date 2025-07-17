from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class User(AbstractUser):
    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="usuarios/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="usuarios/capas/", blank=True, null=True)
    biografia = models.TextField(blank=True)
    endereco = models.CharField(max_length=255)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)
    fone = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15)
    redes_sociais = models.JSONField(blank=True, null=True)
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.PROTECT, null=True)
    is_associado = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")

    def get_tipo_usuario(self):
        if self.is_superuser:
            return "root"
        elif self.is_staff and not self.is_associado:
            return "admin"
        elif self.is_associado and self.nucleos.exists():
            if self.participanucleo_set.filter(is_coordenador=True).exists():
                return "coordenador"
            return "nucleado"
        elif self.is_associado:
            return "associado"
        return "convidado"
