from django.apps import AppConfig


class EventosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "eventos"
    label = "eventos"
    verbose_name = "Eventos"

    def ready(self) -> None:  # pragma: no cover - configuração
        from . import signals  # noqa: F401
