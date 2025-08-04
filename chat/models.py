from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.models import TimeStampedModel

from core.models import SoftDeleteManager, SoftDeleteModel

User = get_user_model()


class ChatChannel(TimeStampedModel, SoftDeleteModel):
    CONTEXT_CHOICES = [
        ("privado", "Privado"),
        ("nucleo", "Núcleo"),
        ("evento", "Evento"),
        ("organizacao", "Organização"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contexto_tipo = models.CharField(max_length=20, choices=CONTEXT_CHOICES)
    contexto_id = models.UUIDField(null=True, blank=True)
    titulo = models.CharField(max_length=200, null=True, blank=True)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to="chat/avatars/", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self) -> str:
        return self.titulo or str(self.id)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("chat:conversation_detail", args=[self.pk])

    class Meta:
        verbose_name = "Canal de Chat"
        verbose_name_plural = "Canais de Chat"


class ChatParticipant(TimeStampedModel):
    channel = models.ForeignKey(
        ChatChannel,
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
        unique_together = ("user", "channel")
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"


class ChatMessage(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        ChatChannel,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    remetente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mensagens_enviadas",
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

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.remetente} - {self.channel_id}"

    class Meta:
        ordering = ["created"]
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"


class ChatNotification(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    mensagem = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    lido = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.usuario} - {self.mensagem_id}"

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


class RelatorioChatExport(TimeStampedModel):
    channel = models.ForeignKey(ChatChannel, on_delete=models.CASCADE)
    formato = models.CharField(max_length=10)
    gerado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="gerando")
    arquivo_url = models.URLField(blank=True)

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
