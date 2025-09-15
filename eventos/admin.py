from django.contrib import admin

from .forms import EventoForm
from .models import (
    BriefingEvento,
    Evento,
    InscricaoEvento,
    MaterialDivulgacaoEvento,
    ParceriaEvento,
    Tarefa,
)


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    form = EventoForm
    list_display = ["titulo", "data_inicio", "data_fim", "cidade", "estado", "status"]


@admin.register(InscricaoEvento)
class InscricaoEventoAdmin(admin.ModelAdmin):
    list_display = ["user", "evento", "presente"]


@admin.register(ParceriaEvento)
class ParceriaEventoAdmin(admin.ModelAdmin):
    list_display = ["evento", "tipo_parceria"]


@admin.register(MaterialDivulgacaoEvento)
class MaterialDivulgacaoEventoAdmin(admin.ModelAdmin):
    list_display = ["evento", "descricao", "tags"]


@admin.register(BriefingEvento)
class BriefingEventoAdmin(admin.ModelAdmin):
    list_display = ["evento", "objetivos"]


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "data_inicio", "data_fim", "status"]
