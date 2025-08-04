import csv
import logging
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from .models import NotificationLog, NotificationTemplate, UserNotificationPreference

logger = logging.getLogger(__name__)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("codigo", "canal", "ativo")
    search_fields = ("codigo",)
    list_filter = ("canal", "ativo")

    actions = ["desativar_templates"]

    def desativar_templates(self, request, queryset):  # pragma: no cover - ação admin
        count = queryset.update(ativo=False)
        self.message_user(request, _(f"{count} templates desativados."))

    desativar_templates.short_description = _("Desativar templates selecionados")

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin
        if obj and NotificationLog.objects.filter(template=obj).exists():
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):  # pragma: no cover - admin
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions


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
    actions = ["exportar_csv"]

    def has_add_permission(self, request):  # pragma: no cover - admin
        return False

    def has_change_permission(self, request, obj=None):  # pragma: no cover - admin
        return False

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin
        return False

    def exportar_csv(self, request, queryset):
        if not request.user.is_staff:
            logger.info("export_logs_denied", extra={"user": request.user.id})
            raise PermissionDenied
        logger.info("export_logs_admin", extra={"user": request.user.id, "count": queryset.count()})
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=notification_logs.csv"
        writer = csv.writer(response)
        writer.writerow(["data_envio", "user", "template", "canal", "status", "erro"])
        for log in queryset:
            writer.writerow([
                log.data_envio,
                log.user_id,
                log.template.codigo,
                log.canal,
                log.status,
                log.erro,
            ])
        return response

    exportar_csv.short_description = _("Exportar CSV")
