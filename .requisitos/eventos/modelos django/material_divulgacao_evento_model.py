
from django.db import models
from model_utils.models import TimeStampedModel


class MaterialDivulgacaoEvento(TimeStampedModel):
    evento = models.ForeignKey(
        "eventos.Evento",
        on_delete=models.CASCADE,
        related_name="materiais_divulgacao"
    )
    arquivo = models.FileField(upload_to="eventos/divulgacao/")
    descricao = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Material de Divulgação"
        verbose_name_plural = "Materiais de Divulgação"

    def __str__(self):
        return f"{self.evento.titulo} - {self.arquivo.name}"
