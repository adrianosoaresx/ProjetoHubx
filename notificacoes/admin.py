import csv
import logging
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from .models import NotificationLog, NotificationTemplate

logger = logging.getLogger(__name__)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):

    list_display = ("codigo", "canal", "deleted")
    search_fields = ("codigo",)
    list_filter = ("canal", "deleted")


    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin
        if obj and NotificationLog.objects.filter(template=obj).exists():
            return False
        return super().has_delete_permission(request, obj)

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
