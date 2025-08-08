from django.contrib import admin

from .models import Nucleo, ParticipacaoNucleo


@admin.register(Nucleo)
class NucleoAdmin(admin.ModelAdmin):
    list_display = ["nome", "organizacao", "created_at", "avatar", "cover"]


@admin.register(ParticipacaoNucleo)
class ParticipacaoNucleoAdmin(admin.ModelAdmin):
    list_display = ["user", "nucleo", "papel", "status"]
