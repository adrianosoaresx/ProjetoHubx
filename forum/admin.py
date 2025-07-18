from django.contrib import admin

from .models import Categoria, Resposta, Topico


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome",)


@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "autor")
    list_filter = ("categoria", "autor")


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    list_display = ("topico", "autor")
    list_filter = ("topico", "autor")
