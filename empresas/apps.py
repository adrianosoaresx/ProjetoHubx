from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "empresas"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from . import signals  # noqa: F401
