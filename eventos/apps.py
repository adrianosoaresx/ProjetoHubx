from django.apps import AppConfig


class EventosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Mantém o label antigo para compatibilidade com ForeignKeys e migrações
    label = "agenda"
    # O app continua a utilizar os módulos do pacote legado ``agenda``
    name = "agenda"
    verbose_name = "Eventos"

    def ready(self) -> None:  # pragma: no cover - configuração
        # Carrega os sinais mantendo compatibilidade com o app legado
        from . import signals  # noqa: F401

