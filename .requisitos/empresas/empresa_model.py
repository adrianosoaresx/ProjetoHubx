
from django.db import models
from model_utils.models import TimeStampedModel


class Tag(TimeStampedModel):
    class Categoria(models.TextChoices):
        PRODUTO = "prod", "Produto"
        SERVICO = "serv", "Serviço"

    nome = models.CharField(max_length=50, unique=True)
    categoria = models.CharField(
        max_length=4,
        choices=Categoria.choices,
        default=Categoria.PRODUTO
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.nome


class Empresa(TimeStampedModel):
    usuario = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="empresas"
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="empresas"
    )
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    tipo = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    descricao = models.TextField(blank=True)
    contato = models.CharField(max_length=255, blank=True)
    palavras_chave = models.CharField(max_length=255, blank=True)
    tags = models.ManyToManyField("empresas.Tag", related_name="empresas", blank=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
