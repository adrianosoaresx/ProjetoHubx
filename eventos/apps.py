from django.apps import AppConfig


class EventosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Mantém o label antigo para compatibilidade com ForeignKeys e migrações
    label = "agenda"
    name = "eventos"
    verbose_name = "Eventos"

    def ready(self) -> None:  # pragma: no cover - configuração
        # Registra os sinais do app de eventos
        from eventos import signals  # noqa: F401
