from __future__ import annotations

from django.contrib import admin

from .models import ConfiguracaoContaLog


@admin.register(ConfiguracaoContaLog)
class ConfiguracaoContaLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "campo",
        "valor_antigo",
        "valor_novo",
        "ip_descriptografado",
        "user_agent_descriptografado",
        "fonte",
        "created_at",
    )
    readonly_fields = list_display

    def ip_descriptografado(self, obj: ConfiguracaoContaLog) -> str | None:
        return obj.ip

    def user_agent_descriptografado(self, obj: ConfiguracaoContaLog) -> str | None:
        return obj.user_agent
