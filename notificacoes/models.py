from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel


class Canal(models.TextChoices):
    EMAIL = "email", _("E-mail")
    PUSH = "push", _("Push")
    WHATSAPP = "whatsapp", _("WhatsApp")
    TODOS = "todos", _("Todos")


class NotificationStatus(models.TextChoices):
    PENDENTE = "pendente", _("Pendente")
    ENVIADA = "enviada", _("Enviada")
    FALHA = "falha", _("Falha")
    LIDA = "lida", _("Lida")


class NotificationTemplate(TimeStampedModel):
    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo: models.SlugField = models.SlugField(unique=True, verbose_name=_("Código"))
    assunto: models.CharField = models.CharField(max_length=200, verbose_name=_("Assunto"))
    corpo: models.TextField = models.TextField(verbose_name=_("Corpo"))
    canal: models.CharField = models.CharField(max_length=20, choices=Canal.choices, verbose_name=_("Canal"))
    ativo: models.BooleanField = models.BooleanField(default=True, verbose_name=_("Ativo"))

    class Meta:
        verbose_name = _("Template de Notificação")
        verbose_name_plural = _("Templates de Notificação")
        permissions = [("can_send_notifications", "Can send notifications")]

    def __str__(self) -> str:  # pragma: no cover - simples
        return self.codigo


class NotificationLog(TimeStampedModel):
    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user: models.ForeignKey = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    destinatario: models.CharField = models.CharField(max_length=254, blank=True)
    template: models.ForeignKey = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    canal: models.CharField = models.CharField(max_length=20, choices=Canal.choices)
    status: models.CharField = models.CharField(
        max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.PENDENTE
    )
    data_envio: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    erro: models.TextField | None = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = _("Log de Notificação")
        verbose_name_plural = _("Logs de Notificação")
        unique_together = ("user", "template", "canal", "created")

    def save(self, *args, **kwargs):  # pragma: no cover - comportamento definido
        if self.pk and NotificationLog.objects.filter(pk=self.pk).exists():
            original = NotificationLog.objects.get(pk=self.pk)
            imutaveis = ["user_id", "template_id", "canal", "destinatario"]
            for campo in imutaveis:
                if getattr(self, campo) != getattr(original, campo):
                    raise PermissionError("NotificationLog é imutável")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - comportamento definido
        raise PermissionError("NotificationLog é imutável")

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.template.codigo} -> {self.user}"  # type: ignore[attr-defined]  # pragma: no cover


class HistoricoNotificacao(TimeStampedModel):
    """Registro de notificações agregadas enviadas aos usuários."""

    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user: models.ForeignKey = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    canal: models.CharField = models.CharField(max_length=20, choices=Canal.choices)
    conteudo: models.JSONField = models.JSONField(default=list)
    enviado_em: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Histórico de Notificação")
        verbose_name_plural = _("Históricos de Notificação")
        ordering = ["-enviado_em"]
        unique_together = ("user", "canal", "enviado_em")

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.user} - {self.canal} - {self.enviado_em:%Y-%m-%d %H:%M}"


class PushSubscription(models.Model):
    """Armazena inscrições de navegadores para notificações Web Push."""

    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    device_id: models.CharField = models.CharField(max_length=255)
    endpoint: models.CharField = models.CharField(max_length=500)
    p256dh: models.CharField = models.CharField(max_length=255)
    auth: models.CharField = models.CharField(max_length=255)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    active: models.BooleanField = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "device_id")
        verbose_name = _("Inscrição Push")
        verbose_name_plural = _("Inscrições Push")

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"{self.user} - {self.device_id}"
