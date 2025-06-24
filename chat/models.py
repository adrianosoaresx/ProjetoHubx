from django.db import models
from django.contrib.auth import get_user_model
from nucleos.models import Nucleo

from core.models import TimeStampedModel

User = get_user_model()


class Mensagem(TimeStampedModel):
    nucleo = models.ForeignKey(Nucleo, on_delete=models.CASCADE)
    remetente = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo = models.CharField(
        choices=[
            ("text", "Texto"),
            ("image", "Imagem"),
            ("video", "Vídeo"),
            ("file", "Arquivo"),
        ],
        max_length=10,
    )
    conteudo = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.remetente}: {self.tipo}"
