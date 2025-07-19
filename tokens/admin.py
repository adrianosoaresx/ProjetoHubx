from django.contrib import admin

from .models import CodigoAutenticacao, TokenAcesso, TOTPDevice


@admin.register(TokenAcesso)
class TokenAcessoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "tipo_destino",
        "estado",
        "gerado_por",
        "usuario",
        "data_expiracao",
    )
    list_filter = ("estado", "tipo_destino")
    search_fields = ("codigo",)


@admin.register(CodigoAutenticacao)
class CodigoAutenticacaoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "codigo",
        "expira_em",
        "verificado",
        "tentativas",
    )
    list_filter = ("verificado",)


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ("usuario", "confirmado", "created_at")
    list_filter = ("confirmado",)
