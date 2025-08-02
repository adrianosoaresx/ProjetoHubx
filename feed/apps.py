from django.apps import AppConfig


class FeedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feed"

    def ready(self) -> None:  # pragma: no cover - importa sinais
        from . import signals  # noqa: F401
