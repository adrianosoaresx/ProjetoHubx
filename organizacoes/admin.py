from django.contrib import admin

from .models import Organizacao


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj"]
