from django.contrib import admin

from .models import CentroCusto, ContaAssociado, LancamentoFinanceiro


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "saldo"]
    search_fields = ["nome"]


@admin.register(ContaAssociado)
class ContaAssociadoAdmin(admin.ModelAdmin):
    list_display = ["user_id", "saldo"]
    search_fields = ["user_id"]


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = ["tipo", "valor", "status", "data_lancamento"]
    list_filter = ["tipo", "status"]
