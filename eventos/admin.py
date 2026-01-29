from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget

from .forms import EventoForm
from .models import BriefingEvento, BriefingTemplate, Evento, InscricaoEvento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    form = EventoForm
    list_display = ["titulo", "data_inicio", "data_fim", "cidade", "estado", "status"]


@admin.register(InscricaoEvento)
class InscricaoEventoAdmin(admin.ModelAdmin):
    list_display = ["user", "evento", "presente"]


TEMPLATE_ALLOWED_GROUPS = ("Admin",)


@admin.register(BriefingTemplate)
class BriefingTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}

    def _has_template_permission(self, request):  # pragma: no cover - admin
        return request.user.is_superuser or request.user.groups.filter(
            name__in=TEMPLATE_ALLOWED_GROUPS
        ).exists()

    def has_add_permission(self, request):  # pragma: no cover - admin
        return self._has_template_permission(request)

    def has_change_permission(self, request, obj=None):  # pragma: no cover - admin
        return self._has_template_permission(request)


@admin.register(BriefingEvento)
class BriefingEventoAdmin(admin.ModelAdmin):
    list_display = ("evento", "template", "status", "orcamento_enviado_em")
    list_filter = ("status", "template__ativo")
    search_fields = ("evento__titulo", "template__nome")

