from django.db import models
from django.contrib.auth import get_user_model


class Organizacao(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    descricao = models.TextField(blank=True)
    logo = models.ImageField(upload_to="organizacoes/logos/", blank=True, null=True)

    class Meta:
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"

    def __str__(self) -> str:
        return self.nome
