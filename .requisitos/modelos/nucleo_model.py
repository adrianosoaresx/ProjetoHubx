
from django.db import models
from model_utils.models import TimeStampedModel


class Nucleo(TimeStampedModel):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='nucleos/avatars/', null=True, blank=True)
    cover = models.ImageField(upload_to='nucleos/capas/', null=True, blank=True)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="nucleos"
    )

    class Meta:
        verbose_name = "Núcleo"
        verbose_name_plural = "Núcleos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ParticipacaoNucleo(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="participacoes_nucleo"
    )
    nucleo = models.ForeignKey(
        Nucleo,
        on_delete=models.CASCADE,
        related_name="participacoes"
    )
    is_coordenador = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "nucleo")
        verbose_name = "Participação em Núcleo"
        verbose_name_plural = "Participações em Núcleos"

    def __str__(self):
        return f"{self.user} em {self.nucleo} ({'Coord.' if self.is_coordenador else 'Membro'})"
