from django.contrib import admin
from .models import Categoria, Topico, Resposta


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome",)


@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "autor", "criado_em")
    list_filter = ("categoria", "autor")


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    list_display = ("topico", "autor", "criado_em")
    list_filter = ("topico", "autor")
