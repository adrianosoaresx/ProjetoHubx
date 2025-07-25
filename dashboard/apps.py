from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"

    def ready(self) -> None:  # pragma: no cover - import signals
        from . import signals  # noqa: F401
