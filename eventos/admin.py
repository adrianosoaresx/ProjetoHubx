from django.contrib import admin
from .models import Evento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "organizacao", "data_hora"]
    filter_horizontal = ["inscritos"]
