from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg
from validate_docbr import CNPJ

from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel


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
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self) -> str:
        return self.nome


class Empresa(TimeStampedModel, SoftDeleteModel):
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
    validado_em = models.DateTimeField(null=True, blank=True)
    fonte_validacao = models.CharField(max_length=50, blank=True, default="")
    # Armazena texto concatenado para busca full-text simplificada.
    search_vector = models.TextField(blank=True, editable=False)
    versao = models.PositiveIntegerField(default=1)

    objects = models.Manager()
    ativos = SoftDeleteManager()

    class Meta:
        ordering = ["nome"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        indexes = [
            models.Index(fields=["cnpj"]),
            models.Index(fields=["municipio"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["deleted"]),
            models.Index(fields=["search_vector"]),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        if not CNPJ().validate(self.cnpj):
            raise ValidationError({"cnpj": "CNPJ inválido"})

    def get_contato_principal(self):
        """Retorna o contato principal da empresa.

        Se houver um contato marcado como ``principal=True`` ele é retornado,
        caso contrário retorna o primeiro contato cadastrado ou ``None`` quando
        não existirem contatos.
        """

        contato = self.contatos.filter(principal=True).first()
        if not contato:
            contato = self.contatos.first()
        return contato

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def soft_delete(self) -> None:  # pragma: no cover - simples
        """Marca o registro como excluído sem removê-lo do banco."""
        super().soft_delete()

    def media_avaliacoes(self) -> float:
        """Retorna a média das avaliações da empresa."""
        return self.avaliacoes.filter(deleted=False).aggregate(avg=Avg("nota"))["avg"] or 0


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


class EmpresaChangeLog(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="logs")
    usuario = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    campo_alterado = models.CharField(max_length=50)
    valor_antigo = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)

    objects = models.Manager()
    ativos = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.empresa.nome} - {self.campo_alterado}"


class AvaliacaoEmpresa(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="avaliacoes")
    usuario = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    nota = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comentario = models.TextField(blank=True)

    objects = models.Manager()
    ativos = SoftDeleteManager()

    class Meta:
        unique_together = ("empresa", "usuario")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.empresa.nome} - {self.usuario.email}"


class FavoritoEmpresa(TimeStampedModel, SoftDeleteModel):
    """Registra empresas favoritas de cada usuário."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="favoritos_empresa")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="favoritos")

    objects = models.Manager()
    ativos = SoftDeleteManager()

    class Meta:
        unique_together = ("usuario", "empresa")
        verbose_name = "Favorito da Empresa"
        verbose_name_plural = "Favoritos das Empresas"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.usuario_id} -> {self.empresa_id}"
