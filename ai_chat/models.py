import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import SoftDeleteManager, SoftDeleteModel, TimeStampedModel


class ChatSession(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Ativa")
        CLOSED = "closed", _("Encerrada")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sessão de Chat"
        verbose_name_plural = "Sessões de Chat"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"Sessão {self.pk} ({self.get_status_display()})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class ChatMessage(TimeStampedModel, SoftDeleteModel):
    class Role(models.TextChoices):
        USER = "user", _("Usuário")
        ASSISTANT = "assistant", _("Assistente")
        TOOL = "tool", _("Ferramenta")

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    organizacao = models.ForeignKey(
        "organizacoes.Organizacao",
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    tool_call_id = models.CharField(max_length=255, blank=True, null=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mensagem de Chat"
        verbose_name_plural = "Mensagens de Chat"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.get_role_display()} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    def clean(self) -> None:
        super().clean()
        if (
            self.session_id
            and self.organizacao_id
            and self.session.organizacao_id != self.organizacao_id
        ):
            raise ValidationError(
                {"organizacao": _("A organização da sessão e da mensagem devem ser iguais.")}
            )

    def save(self, *args, **kwargs):  # pragma: no cover - comportamento simples
        if self.session_id and not self.organizacao_id:
            self.organizacao = self.session.organizacao
        self.full_clean()
        super().save(*args, **kwargs)
