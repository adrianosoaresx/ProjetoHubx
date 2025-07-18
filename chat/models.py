from django.contrib.auth import get_user_model
from django.db import models

from core.models import TimeStampedModel
from nucleos.models import Nucleo

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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return f"Para {self.usuario} de {self.remetente}"


class ChatConversation(TimeStampedModel):
    TIPO_CONVERSA_CHOICES = [
        ("direta", "Mensagem direta"),
        ("grupo", "Grupo global"),
        ("organizacao", "Grupo da Organização"),
        ("nucleo", "Grupo do Núcleo"),
        ("evento", "Grupo do Evento"),
    ]

    titulo = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(unique=True)
    tipo_conversa = models.CharField(max_length=20, choices=TIPO_CONVERSA_CHOICES)
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao", null=True, blank=True, on_delete=models.SET_NULL
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo", null=True, blank=True, on_delete=models.SET_NULL
    )
    evento = models.ForeignKey(
        "agenda.Evento", null=True, blank=True, on_delete=models.SET_NULL
    )
    imagem = models.ImageField(upload_to="chat/avatars/", null=True, blank=True)

    class Meta:
        verbose_name = "Conversa"
        verbose_name_plural = "Conversas"


class ChatParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "conversation")
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"


class ChatMessage(TimeStampedModel):
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.TextField()
    arquivo = models.FileField(upload_to="chat/arquivos/", null=True, blank=True)
    lido_por = models.ManyToManyField(
        User, related_name="mensagens_lidas", blank=True
    )

    class Meta:
        ordering = ["created"]
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"


class ChatNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mensagem = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    lido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
