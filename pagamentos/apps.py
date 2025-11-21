from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PagamentosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pagamentos"
    verbose_name = _("Pagamentos")
