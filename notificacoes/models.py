from __future__ import annotations

from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel


class Canal(models.TextChoices):
    EMAIL = "email", "E-mail"
    PUSH = "push", "Push"
    WHATSAPP = "whatsapp", "WhatsApp"
    TODOS = "todos", "Todos"


class NotificationStatus(models.TextChoices):
    ENVIADA = "enviada", "Enviada"
    FALHA = "falha", "Falha"


class NotificationTemplate(models.Model):
    codigo: models.SlugField = models.SlugField(unique=True)
    assunto: models.CharField = models.CharField(max_length=200)
    corpo: models.TextField = models.TextField()
    canal: models.CharField = models.CharField(max_length=20, choices=Canal.choices)
    ativo: models.BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Template de Notificação"
        verbose_name_plural = "Templates de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.codigo


class UserNotificationPreference(models.Model):
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferencias_notificacoes",
    )
    email: models.BooleanField = models.BooleanField(default=True)
    push: models.BooleanField = models.BooleanField(default=True)
    whatsapp: models.BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Preferência de Notificação"
        verbose_name_plural = "Preferências de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"Preferências de {self.user}"


class NotificationLog(TimeStampedModel):
    user: models.ForeignKey = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    template: models.ForeignKey = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    canal: models.CharField = models.CharField(max_length=20, choices=Canal.choices)
    status: models.CharField = models.CharField(max_length=20, choices=NotificationStatus.choices)
    data_envio: models.DateTimeField = models.DateTimeField()
    erro: models.TextField | None = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Log de Notificação"
        verbose_name_plural = "Logs de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.template.codigo} -> {self.user}"  # type: ignore[attr-defined]  # pragma: no cover
