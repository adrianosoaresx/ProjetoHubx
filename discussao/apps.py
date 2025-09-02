from django.apps import AppConfig


class DiscussaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discussao"

    def ready(self) -> None:  # pragma: no cover - apenas registra sinais
        from . import signals  # noqa: F401
