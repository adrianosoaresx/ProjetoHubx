from django.contrib import admin

from .models import (
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    ImportacaoPagamentos,
    LancamentoFinanceiro,
)


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "saldo"]
    search_fields = ["nome"]


@admin.register(ContaAssociado)
class ContaAssociadoAdmin(admin.ModelAdmin):
    list_display = ["user", "saldo"]
    search_fields = ["user__email"]


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = ["tipo", "valor", "status", "data_lancamento"]
    list_filter = ["tipo", "status"]


@admin.register(ImportacaoPagamentos)
class ImportacaoPagamentosAdmin(admin.ModelAdmin):
    list_display = ["arquivo", "usuario", "total_processado", "created_at"]
    search_fields = ["arquivo", "usuario__email"]


@admin.register(FinanceiroLog)
class FinanceiroLogAdmin(admin.ModelAdmin):
    list_display = ["acao", "usuario", "created_at"]
    list_filter = ["acao"]


