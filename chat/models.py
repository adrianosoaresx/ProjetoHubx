from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import models

from core.models import (
    SoftDeleteManager,
    SoftDeleteModel,
    TimeStampedModel as CoreTimeStampedModel,
)

User = get_user_model()


class ChatChannelCategory(CoreTimeStampedModel, SoftDeleteModel):
    """Categoria para organização de canais de chat."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover - simple
        return self.nome

    class Meta:
        verbose_name = "Categoria de Canal"
        verbose_name_plural = "Categorias de Canal"


class ChatChannel(CoreTimeStampedModel, SoftDeleteModel):
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
    e2ee_habilitado = models.BooleanField(default=False)
    retencao_dias = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Quantidade de dias para manter mensagens antes da remoção automática",
    )
    categoria = models.ForeignKey(
        ChatChannelCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="channels",
    )

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


class ChatParticipant(CoreTimeStampedModel, SoftDeleteModel):
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
        unique_together = ("user", "channel", "deleted")
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"


class ChatMessage(CoreTimeStampedModel, SoftDeleteModel):
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
    conteudo_cifrado = models.TextField(blank=True)
    arquivo = models.FileField(upload_to="chat/arquivos/", null=True, blank=True)
    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="respostas",
    )
    pinned_at = models.DateTimeField(null=True, blank=True)
    reactions = models.ManyToManyField(
        User,
        through="ChatMessageReaction",
        related_name="message_reactions",
        blank=True,
    )
    lido_por = models.ManyToManyField(User, related_name="mensagens_lidas", blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    is_spam = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.remetente} - {self.channel_id}"

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"

    def reaction_counts(self) -> dict[str, int]:
        """Return a mapping of emoji to count of reactions."""
        from django.db.models import Count

        return dict(self.reaction_details.values("emoji").annotate(c=Count("id")).values_list("emoji", "c"))

    def restore_from_log(self, log: "ChatModerationLog", moderator: User) -> None:
        """Restore message content from a moderation log.

        Saves the previous content in a new moderation log entry so the
        restoration itself is tracked for transparency.
        """
        previous = self.conteudo
        self.conteudo = log.previous_content
        self.save(update_fields=["conteudo"])
        ChatModerationLog.objects.create(
            message=self,
            action="edit",
            moderator=moderator,
            previous_content=previous,
        )


class ChatMessageReaction(CoreTimeStampedModel, SoftDeleteModel):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="reaction_details")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_reactions")
    emoji = models.CharField(max_length=32)

    class Meta:
        unique_together = ("message", "user", "emoji", "deleted")
        verbose_name = "Reação"
        verbose_name_plural = "Reações"


class ChatNotification(CoreTimeStampedModel, SoftDeleteModel):
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


class ChatMessageFlag(CoreTimeStampedModel, SoftDeleteModel):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="flags")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("message", "user", "deleted")
        verbose_name = "Sinalização"
        verbose_name_plural = "Sinalizações"


class ChatFavorite(CoreTimeStampedModel, SoftDeleteModel):
    """Marcações pessoais de mensagens favoritas."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_favorites")
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        unique_together = ("user", "message", "deleted")
        indexes = [models.Index(fields=["user", "message", "deleted"])]
        verbose_name = "Favorito"
        verbose_name_plural = "Favoritos"


class ChatAttachment(CoreTimeStampedModel, SoftDeleteModel):
    """Metadados de arquivos enviados no chat."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mensagem = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    arquivo = models.FileField(upload_to="chat/attachments/")
    mime_type = models.CharField(max_length=100, blank=True)
    tamanho = models.PositiveIntegerField(default=0)
    thumb_url = models.URLField(blank=True)
    preview_ready = models.BooleanField(default=False)
    infected = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"


class RelatorioChatExport(CoreTimeStampedModel):
    channel = models.ForeignKey(ChatChannel, on_delete=models.CASCADE)
    formato = models.CharField(max_length=10)
    gerado_por = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="gerando")
    arquivo_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Relatório de Exportação"
        verbose_name_plural = "Relatórios de Exportação"


class ChatModerationLog(CoreTimeStampedModel):
    ACTION_CHOICES = [
        ("approve", "Aprovar"),
        ("remove", "Remover"),
        ("edit", "Editar"),
        ("create_item", "Criar item"),
        ("retencao", "Retenção"),
        ("spam", "Spam"),
    ]

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="moderations")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_moderations")
    previous_content = models.TextField(blank=True)

    class Meta:
        verbose_name = "Log de Moderação"
        verbose_name_plural = "Logs de Moderação"


class TrendingTopic(CoreTimeStampedModel):
    canal = models.ForeignKey(
        ChatChannel,
        on_delete=models.CASCADE,
        related_name="trending_topics",
    )
    palavra = models.CharField(max_length=100)
    frequencia = models.PositiveIntegerField()
    periodo_inicio = models.DateTimeField()
    periodo_fim = models.DateTimeField()

    class Meta:
        ordering = ["-frequencia"]
        verbose_name = "Tópico em Alta"
        verbose_name_plural = "Tópicos em Alta"


class ResumoChat(CoreTimeStampedModel):
    PERIODOS = [("diario", "Diário"), ("semanal", "Semanal")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canal = models.ForeignKey(ChatChannel, on_delete=models.CASCADE, related_name="resumos")
    periodo = models.CharField(max_length=10, choices=PERIODOS)
    conteudo = models.TextField()
    detalhes = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Resumo de Chat"
        verbose_name_plural = "Resumos de Chat"


class UserChatPreference(CoreTimeStampedModel):
    """Preferências de uso do chat por usuário."""

    THEME_CHOICES = [("claro", "Claro"), ("escuro", "Escuro")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="chat_preference",
    )
    tema = models.CharField(max_length=10, choices=THEME_CHOICES, default="claro")
    buscas_salvas = models.JSONField(default=list, blank=True)
    resumo_diario = models.BooleanField(default=False)
    resumo_semanal = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Preferência de Chat"
        verbose_name_plural = "Preferências de Chat"
