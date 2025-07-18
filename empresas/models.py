from django.contrib.auth import get_user_model
from django.db import models

from core.models import TimeStampedModel


class Tag(TimeStampedModel):
    """Tags para produtos e serviços."""

    class Categoria(models.TextChoices):
        PRODUTO = "prod", "Produto"
        SERVICO = "serv", "Serviço"

    nome = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(
        max_length=4,
        choices=Categoria.choices,
        default=Categoria.PRODUTO,
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:
        return self.nome


class Empresa(TimeStampedModel):
    usuario = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="empresas"
    )
    cnpj = models.CharField(max_length=18, unique=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    ramo_atividade = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    endereco = models.TextField()
    banner = models.ImageField(upload_to="empresas/banners/", blank=True, null=True)
    descricao = models.TextField(blank=True)
    contato = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self) -> str:
        return self.razao_social


class ContatoEmpresa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="contatos")
    nome = models.CharField(max_length=255)
    cargo = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20)
    principal = models.BooleanField(default=False)

    class Meta:
        unique_together = ("empresa", "email")
        verbose_name = "Contato da Empresa"
        verbose_name_plural = "Contatos das Empresas"

    def __str__(self) -> str:
        return f"{self.nome} ({self.cargo})"
