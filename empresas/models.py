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

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome


class Empresa(TimeStampedModel):
    usuario = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="empresas"
    )
    cnpj = models.CharField(max_length=18, unique=True)
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    descricao = models.TextField(blank=True)
    contato = models.CharField(max_length=255, blank=True)
    palavras_chave = models.CharField(max_length=255, blank=True)
    tags = models.ManyToManyField(Tag, related_name="empresas", blank=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self) -> str:  # pragma: no cover
        return self.nome
