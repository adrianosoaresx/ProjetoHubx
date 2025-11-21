from __future__ import annotations

from django.contrib import admin

from pagamentos.models import Pedido, Transacao


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "valor", "status", "email", "criado_em")
    list_filter = ("status", "criado_em")
    search_fields = ("id", "email", "external_id")
    ordering = ("-criado_em",)


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "metodo", "status", "valor", "criado_em")
    list_filter = ("status", "metodo", "criado_em")
    search_fields = ("id", "external_id", "pedido__email")
    ordering = ("-criado_em",)
