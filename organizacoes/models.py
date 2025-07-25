import uuid

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Organizacao(TimeStampedModel):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    descricao = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    avatar = models.ImageField(upload_to="organizacoes/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="organizacoes/capas/", blank=True, null=True)
    deleted = models.BooleanField(default=False)
    inativa = models.BooleanField(default=False)
    inativada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class OrganizacaoLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    acao = models.CharField(max_length=50)
    dados_antigos = models.JSONField(default=dict, blank=True)
    dados_novos = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organizacao} - {self.acao}"
