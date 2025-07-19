from django.contrib import admin

from .models import ContatoEmpresa, Empresa, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["razao_social", "cnpj", "usuario"]
    search_fields = ["razao_social", "nome_fantasia", "cnpj"]
    list_filter = ["estado"]


@admin.register(ContatoEmpresa)
class ContatoEmpresaAdmin(admin.ModelAdmin):
    list_display = ["nome", "email", "empresa", "principal"]
    search_fields = ["nome", "email"]
    list_filter = ["principal"]
