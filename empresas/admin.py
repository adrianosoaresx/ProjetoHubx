from django.contrib import admin

from .models import (
    AvaliacaoEmpresa,
    ContatoEmpresa,
    Empresa,
    EmpresaChangeLog,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "usuario", "deleted"]
    search_fields = ["nome", "cnpj", "palavras_chave"]
    list_filter = ["estado", "tipo", "deleted"]


@admin.register(ContatoEmpresa)
class ContatoEmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "email", "empresa", "principal"]
    search_fields = ["nome", "email"]
    list_filter = ["principal"]


@admin.register(AvaliacaoEmpresa)
class AvaliacaoEmpresaAdmin(admin.ModelAdmin):
    list_display = ["empresa", "usuario", "nota", "created"]
    search_fields = ["empresa__nome", "usuario__email"]
    list_filter = ["nota"]


@admin.register(EmpresaChangeLog)
class EmpresaChangeLogAdmin(admin.ModelAdmin):
    list_display = ["empresa", "campo_alterado", "alterado_em", "usuario"]
    search_fields = ["empresa__nome", "campo_alterado", "usuario__email"]
    list_filter = ["campo_alterado"]
