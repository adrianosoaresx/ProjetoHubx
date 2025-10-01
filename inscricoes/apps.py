from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InscricoesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inscricoes"
    verbose_name = _("Inscrições")
