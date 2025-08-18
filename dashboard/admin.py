from django.contrib import admin

from .models import DashboardCustomMetric


@admin.register(DashboardCustomMetric)
class DashboardCustomMetricAdmin(admin.ModelAdmin):
    list_display = ("code", "nome", "escopo")
    search_fields = ("code", "nome")

