from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import NotificationLog, NotificationTemplate, UserNotificationPreference


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("codigo", "canal", "ativo", "deleted")
    search_fields = ("codigo",)
    list_filter = ("canal", "ativo", "deleted")

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin
        if obj and NotificationLog.objects.filter(template=obj).exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "push", "whatsapp")
    search_fields = ("user__email",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "template", "canal", "status", "data_envio")
    search_fields = ("user__email", "template__codigo")
    list_filter = ("status", "canal")
    readonly_fields = ("user", "template", "canal", "status", "data_envio", "erro")

    def has_add_permission(self, request):  # pragma: no cover - admin
        return False

    def has_change_permission(self, request, obj=None):  # pragma: no cover - admin
        return False

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin
        return False
