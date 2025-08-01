from __future__ import annotations

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .services import metrics


class NotificacoesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "notificacoes"

    def ready(self) -> None:  # pragma: no cover - integração
        # validação de variáveis de ambiente
        required = [
            "NOTIFICATIONS_EMAIL_API_URL",
            "NOTIFICATIONS_EMAIL_API_KEY",
            "NOTIFICATIONS_PUSH_API_URL",
            "NOTIFICATIONS_PUSH_API_KEY",
            "NOTIFICATIONS_WHATSAPP_API_URL",
            "NOTIFICATIONS_WHATSAPP_API_KEY",
        ]
        missing = [name for name in required if not getattr(settings, name, "")]
        if missing:
            raise ImproperlyConfigured(
                f"Missing notification settings: {', '.join(missing)}"
            )

        from .models import NotificationTemplate
        from . import signals

        try:
            metrics.templates_total.set(
                NotificationTemplate.objects.filter(ativo=True).count()
            )
        except Exception:  # pragma: no cover - durante migrações
            metrics.templates_total.set(0)

        signals.definir_template_default.send(sender=self.__class__)

