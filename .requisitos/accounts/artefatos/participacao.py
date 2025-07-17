from django.db import models
from django.conf import settings

class ParticipacaoNucleo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nucleo = models.ForeignKey("nucleos.Nucleo", on_delete=models.CASCADE)
    is_coordenador = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "nucleo")
        verbose_name = "participação em núcleo"
        verbose_name_plural = "participações em núcleos"

    def __str__(self):
        return f"{self.user} em {self.nucleo} ({'Coord.' if self.is_coordenador else 'Membro'})"
