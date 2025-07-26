from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

User = get_user_model()


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
    tipo_conversa = models.CharField(
        max_length=12,
        choices=TIPO_CONVERSA_CHOICES,
        default="direta",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    nucleo = models.ForeignKey(
        "nucleos.Nucleo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    evento = models.ForeignKey("agenda.Evento", null=True, blank=True, on_delete=models.SET_NULL)
    imagem = models.ImageField(upload_to="chat/avatars/", null=True, blank=True)

    def __str__(self) -> str:
        return self.titulo or self.slug

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("chat:conversation_detail", args=[self.slug])

    class Meta:
        verbose_name = "Conversa"
        verbose_name_plural = "Conversas"


class ChatParticipant(models.Model):
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_participations",
    )
    is_admin = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "conversation")
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"


class ChatMessage(TimeStampedModel):
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    MESSAGE_TYPES = [
        ("text", "Texto"),
        ("image", "Imagem"),
        ("video", "Vídeo"),
        ("file", "Arquivo"),
    ]

    tipo = models.CharField(max_length=10, choices=MESSAGE_TYPES, default="text")
    conteudo = models.TextField(blank=True)
    arquivo = models.FileField(upload_to="chat/arquivos/", null=True, blank=True)
    pinned_at = models.DateTimeField(null=True, blank=True)
    reactions = models.JSONField(default=dict, blank=True)
    lido_por = models.ManyToManyField(User, related_name="mensagens_lidas", blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.sender} - {self.conversation.slug}"

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"


class ChatNotification(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    mensagem = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    lido = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user} - {self.mensagem_id}"

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"


class ChatMessageFlag(TimeStampedModel):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="flags")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("message", "user")
        verbose_name = "Sinalização"
        verbose_name_plural = "Sinalizações"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        total = self.message.flags.count()
        if total >= 3 and not self.message.hidden_at:
            self.message.hidden_at = timezone.now()
            self.message.save(update_fields=["hidden_at", "updated_at"])


class RelatorioChatExport(TimeStampedModel):
    channel = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    formato = models.CharField(max_length=10)
    gerado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    arquivo_url = models.URLField()

    class Meta:
        verbose_name = "Relatório de Exportação"
        verbose_name_plural = "Relatórios de Exportação"


class ChatModerationLog(TimeStampedModel):
    ACTION_CHOICES = [("approve", "Aprovar"), ("remove", "Remover")]

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="moderations")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_moderations")

    class Meta:
        verbose_name = "Log de Moderação"
        verbose_name_plural = "Logs de Moderação"
