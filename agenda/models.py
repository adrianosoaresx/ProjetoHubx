from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from core.fields import URLField
from core.models import TimeStampedModel
from organizacoes.models import Organizacao

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

    def __str__(self) -> str:
        return self.titulo


class FeedbackNota(models.Model):
    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name="feedbacks"
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("evento", "usuario")
        verbose_name = "Feedback do Evento"
        verbose_name_plural = "Feedbacks dos Eventos"

    def __str__(self):
        return f"{self.usuario} → {self.evento} [{self.nota}]"
