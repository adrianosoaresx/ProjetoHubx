from django.contrib import admin

from .models import NotificationSettings


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ["user", "email_conexoes", "sistema_conexoes"]
