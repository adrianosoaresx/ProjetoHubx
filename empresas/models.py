from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from validate_docbr import CNPJ

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
    usuario = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="empresas")
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.CASCADE, related_name="empresas")
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    ramo_atividade = models.CharField(max_length=100)
    endereco = models.CharField(max_length=255)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    cep = models.CharField(max_length=9)
    email_corporativo = models.EmailField()
    telefone_corporativo = models.CharField(max_length=20)
    site = models.URLField(blank=True)
    rede_social = models.URLField(blank=True)
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    banner = models.ImageField(upload_to="empresas/banners/", blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name="empresas", blank=True)

    class Meta:
        ordering = ["razao_social"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self) -> str:
        return self.razao_social

    def clean(self) -> None:
        if not CNPJ().validate(self.cnpj):
            raise ValidationError({"cnpj": "CNPJ inválido"})


class ContatoEmpresa(TimeStampedModel):
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

    def save(self, *args, **kwargs):
        if self.principal:
            ContatoEmpresa.objects.filter(empresa=self.empresa, principal=True).exclude(pk=self.pk).update(
                principal=False
            )
        super().save(*args, **kwargs)
