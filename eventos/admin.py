from django.contrib import admin

from .forms import EventoForm
from .models import Evento, InscricaoEvento


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    form = EventoForm
    list_display = ["titulo", "data_inicio", "data_fim", "cidade", "estado", "status"]


@admin.register(InscricaoEvento)
class InscricaoEventoAdmin(admin.ModelAdmin):
    list_display = ["user", "evento", "presente"]


