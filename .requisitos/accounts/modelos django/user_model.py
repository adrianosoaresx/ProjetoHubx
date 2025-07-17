
from django.contrib.auth.models import AbstractUser
from django.db import models
from model_utils.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='usuarios/avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='usuarios/capas/', blank=True, null=True)
    biografia = models.TextField(blank=True)
    endereco = models.CharField(max_length=255)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)
    fone = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15)
    redes_sociais = models.JSONField(blank=True, null=True)

    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.PROTECT,
        null=True
    )

    is_associado = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    nucleos = models.ManyToManyField(
        "nucleos.Nucleo",
        through="accounts.ParticipacaoNucleo",
        related_name="usuarios"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.nome_completo

    def get_tipo_usuario(self):
        if self.is_superuser:
            return "root"
        if self.is_staff and not self.is_associado:
            return "admin"
        if not self.is_associado:
            return "convidado"
        if self.participacoes_nucleo.filter(is_coordenador=True).exists():
            return "coordenador"
        if self.participacoes_nucleo.exists():
            return "nucleado"
        return "associado"

    def is_coordenador_do(self, nucleo):
        return self.participacoes_nucleo.filter(nucleo=nucleo, is_coordenador=True).exists()


class ParticipacaoNucleo(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    nucleo = models.ForeignKey("nucleos.Nucleo", on_delete=models.CASCADE)
    is_coordenador = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'nucleo')
        verbose_name = "Participação em Núcleo"
        verbose_name_plural = "Participações em Núcleos"

    def __str__(self):
        return f"{self.user} em {self.nucleo} ({'Coord.' if self.is_coordenador else 'Membro'})"
