from django.contrib import admin

from .models import Empresa, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "usuario"]
    search_fields = ["nome", "cnpj", "palavras_chave"]
    list_filter = ["estado"]
