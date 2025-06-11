from django.conf import settings
from django.db import models


class NotificationSettings(models.Model):
    """Preferências de notificação do usuário."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_settings")
    email_conexoes = models.BooleanField(default=True)
    email_mensagens = models.BooleanField(default=True)
    email_eventos = models.BooleanField(default=True)
    email_newsletter = models.BooleanField(default=True)
    sistema_conexoes = models.BooleanField(default=True)
    sistema_mensagens = models.BooleanField(default=True)
    sistema_eventos = models.BooleanField(default=True)
    sistema_comentarios = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuração de Notificação"
        verbose_name_plural = "Configurações de Notificação"

    def __str__(self) -> str:  # pragma: no cover - simples
        return f"Notificações de {self.user}"
