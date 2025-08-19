from django.apps import AppConfig


class OrganizacoesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organizacoes"

    def ready(self) -> None:  # pragma: no cover - importa sinais
        from . import signals  # noqa: F401
