
from django.db import models
from model_utils.models import TimeStampedModel


class Organizacao(TimeStampedModel):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='organizacoes/avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='organizacoes/capas/', blank=True, null=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
