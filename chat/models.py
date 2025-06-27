from django.db import models
from django.contrib.auth import get_user_model
from nucleos.models import Nucleo

from core.models import TimeStampedModel

User = get_user_model()


class Mensagem(TimeStampedModel):
    nucleo = models.ForeignKey(Nucleo, on_delete=models.CASCADE)
    remetente = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="mensagens_enviadas"
    )
    destinatario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mensagens_recebidas",
        null=True,
        blank=True,
    )
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


class Notificacao(TimeStampedModel):

    """Registra notificações de novas mensagens."""

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    remetente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificacoes_enviadas",
    )
    mensagem = models.ForeignKey(
        Mensagem,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )

    lida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self) -> str:  # pragma: no cover - simples

        return f"Para {self.usuario} de {self.remetente}"

