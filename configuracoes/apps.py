from __future__ import annotations

from django.apps import AppConfig


class ConfiguracoesConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "configuracoes"

    def ready(self) -> None:  # pragma: no cover - import side effects
        from . import signals  # noqa: F401
