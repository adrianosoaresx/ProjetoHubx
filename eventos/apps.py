from django.apps import AppConfig


class EventosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Mantém o label antigo para compatibilidade com ForeignKeys e migrações
    label = "agenda"
    name = "eventos"
    verbose_name = "Eventos"

    def ready(self) -> None:  # pragma: no cover - configuração
        # Reutiliza os sinais do app legado
        from agenda import signals  # noqa: F401
