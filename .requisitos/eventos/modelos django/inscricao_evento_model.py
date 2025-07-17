
from django.db import models
from model_utils.models import TimeStampedModel
from django.core.validators import MinValueValidator, MaxValueValidator


class InscricaoEvento(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="inscricoes_evento"
    )
    evento = models.ForeignKey(
        "eventos.Evento",
        on_delete=models.CASCADE,
        related_name="inscricoes"
    )
    presente = models.BooleanField(default=False)
    avaliacao = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    valor_pago = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    observacao = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "evento")
        verbose_name = "Inscrição em Evento"
        verbose_name_plural = "Inscrições em Eventos"

    def __str__(self):
        return f"{self.user} em {self.evento}"

    def pode_avaliar(self):
        return (
            self.evento.status == 1 and
            self.evento.data_fim and
            self.evento.data_fim < self.modified
        )
