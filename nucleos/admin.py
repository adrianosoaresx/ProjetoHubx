from django.contrib import admin

from .models import ConviteNucleo, CoordenadorSuplente, Nucleo, ParticipacaoNucleo


@admin.register(Nucleo)
class NucleoAdmin(admin.ModelAdmin):
    list_display = ["nome", "organizacao", "created_at", "deleted", "deleted_at", "avatar", "cover"]


@admin.register(ParticipacaoNucleo)
class ParticipacaoNucleoAdmin(admin.ModelAdmin):
    list_display = ["user", "nucleo", "papel", "status"]


@admin.register(CoordenadorSuplente)
class CoordenadorSuplenteAdmin(admin.ModelAdmin):
    list_display = ["nucleo", "usuario", "periodo_inicio", "periodo_fim"]
    list_filter = ["nucleo", "usuario"]


@admin.register(ConviteNucleo)
class ConviteNucleoAdmin(admin.ModelAdmin):
    list_display = ["email", "papel", "nucleo", "data_expiracao", "usado_em"]
    list_filter = ["papel", "nucleo", "data_expiracao", "usado_em"]
