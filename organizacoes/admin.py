from django.contrib import admin

from .forms import OrganizacaoForm
from .models import Organizacao


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "avatar"]
    search_fields = ["nome", "cnpj"]
    form = OrganizacaoForm
