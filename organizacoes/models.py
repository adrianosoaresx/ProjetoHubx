from django.db import models

from core.models import TimeStampedModel


class Organizacao(TimeStampedModel):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    descricao = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    avatar = models.ImageField(upload_to="organizacoes/avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="organizacoes/capas/", blank=True, null=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome
