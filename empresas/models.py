from __future__ import annotations

import uuid

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="empresas")
    organizacao = models.ForeignKey("organizacoes.Organizacao", on_delete=models.CASCADE, related_name="empresas")
    nome = models.CharField(max_length=255, default="")
    cnpj = models.CharField(max_length=18, unique=True)
    tipo = models.CharField(max_length=50, default="")
    municipio = models.CharField(max_length=100, default="")
    estado = models.CharField(max_length=2, default="")
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    descricao = models.TextField(blank=True)
    palavras_chave = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name="empresas", blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        indexes = [
            models.Index(fields=["cnpj"]),
            models.Index(fields=["municipio"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["deleted"]),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        if not CNPJ().validate(self.cnpj):
            raise ValidationError({"cnpj": "CNPJ inválido"})

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def soft_delete(self) -> None:
        """Marca o registro como excluído sem removê-lo do banco."""
        self.deleted = True
        self.save(update_fields=["deleted"])

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        self.soft_delete()


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


class EmpresaChangeLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="logs")
    usuario = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )
    campo_alterado = models.CharField(max_length=50)
    valor_antigo = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)
    alterado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-alterado_em"]

    def __str__(self) -> str:
        return f"{self.empresa.nome} - {self.campo_alterado}"


class AvaliacaoEmpresa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="avaliacoes")
    usuario = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    nota = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comentario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("empresa", "usuario")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.empresa.nome} - {self.usuario.email}"
