from django.contrib import admin

from .models import (
    Carteira,
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


@admin.register(Carteira)
class CarteiraAdmin(admin.ModelAdmin):
    list_display = ["nome", "centro_custo", "tipo", "saldo", "created_at"]
    list_filter = ["tipo", "centro_custo"]
    search_fields = ["nome", "centro_custo__nome"]


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


