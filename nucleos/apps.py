from django.apps import AppConfig


class NucleosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nucleos"
    def ready(self):
        from . import signals  # noqa: F401

