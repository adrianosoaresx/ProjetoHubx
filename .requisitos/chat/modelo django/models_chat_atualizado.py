
from django.db import models
from django.contrib.auth import get_user_model

from core.models import TimeStampedModel
from nucleos.models import Nucleo
from eventos.models import Evento
from organizacoes.models import Organizacao

User = get_user_model()

class Mensagem(TimeStampedModel):
    remetente = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="mensagens_enviadas"
    )
    destinatario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mensagens_recebidas",
        null=True, blank=True,
    )

    # Escopos reutilizáveis
    nucleo = models.ForeignKey(Nucleo, on_delete=models.CASCADE, null=True, blank=True)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, null=True, blank=True)
    organizacao = models.ForeignKey(Organizacao, on_delete=models.CASCADE, null=True, blank=True)

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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.remetente} -> {self.destinatario or 'grupo'}: {self.tipo}"


class Notificacao(TimeStampedModel):
    """Notificação de nova mensagem"""

    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notificacoes"
    )
    remetente = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notificacoes_enviadas"
    )
    mensagem = models.ForeignKey(
        Mensagem, on_delete=models.CASCADE, related_name="notificacoes"
    )

    lida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self):
        return f"Para {self.usuario} de {self.remetente}"
