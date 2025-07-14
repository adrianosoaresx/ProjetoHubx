from django.db import models
from django.contrib.auth import get_user_model
from organizacoes.models import Organizacao

from core.models import TimeStampedModel
from core.fields import URLField

User = get_user_model()


class Evento(TimeStampedModel):
    organizacao = models.ForeignKey(
        Organizacao, on_delete=models.CASCADE, related_name="eventos"
    )
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    data_hora = models.DateTimeField()
    duracao = models.DurationField(help_text="Duração do evento")
    link_inscricao = URLField(blank=True)
    briefing = models.TextField(blank=True)
    inscritos = models.ManyToManyField(
        User, related_name="eventos_inscritos", blank=True
    )

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ["-data_hora"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.titulo


__all__ = ["Evento"]
