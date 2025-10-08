from django.contrib import admin

from .models import Organizacao


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "slug", "avatar", "cover"]
    prepopulated_fields = {"slug": ("nome",)}
