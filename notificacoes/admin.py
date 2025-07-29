from django.contrib import admin

from .models import NotificationLog, NotificationTemplate, UserNotificationPreference


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("codigo", "canal", "ativo")
    search_fields = ("codigo",)
    list_filter = ("canal", "ativo")


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "push", "whatsapp")
    search_fields = ("user__email",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "template", "canal", "status", "data_envio")
    search_fields = ("user__email", "template__codigo")
    list_filter = ("status", "canal")
