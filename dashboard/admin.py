from django.contrib import admin

from .models import MetricDefinition

@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "titulo", "provider", "publico", "ativo")
    search_fields = ("code", "titulo", "descricao")
    list_filter = ("publico", "ativo", "provider")
    autocomplete_fields = ("owner",)
