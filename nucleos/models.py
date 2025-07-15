from django.contrib.auth import get_user_model
from django.db import models

from core.models import TimeStampedModel
from organizacoes.models import Organizacao

User = get_user_model()


class Nucleo(TimeStampedModel):
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="nucleos",
        db_column="organizacao",
    )
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="nucleos/avatars/", blank=True, null=True)
    data_criacao = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Núcleo"
        verbose_name_plural = "Núcleos"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.nome
