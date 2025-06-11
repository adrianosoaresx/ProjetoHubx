from django.contrib import admin

from .models import Perfil, NotificationSettings


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["user", "telefone", "cidade"]
    search_fields = ["user__username", "cidade"]


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ["user", "email_conexoes", "sistema_conexoes"]
