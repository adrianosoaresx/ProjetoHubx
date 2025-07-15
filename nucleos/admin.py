from django.contrib import admin

from .models import Nucleo


@admin.register(Nucleo)
class NucleoAdmin(admin.ModelAdmin):
    list_display = ["nome", "organizacao", "data_criacao"]
