from decimal import Decimal

from django.contrib import admin
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import (
    Carteira,
    CentroCusto,
    ContaAssociado,
    FinanceiroLog,
    ImportacaoPagamentos,
    LancamentoFinanceiro,
)


ZERO = Decimal("0")


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "carteiras_ativas", "saldo_em_carteiras"]
    search_fields = ["nome"]

    def get_queryset(self, request):  # type: ignore[override]
        queryset = super().get_queryset(request)
        return queryset.annotate(
            carteiras_ativas_total=Count(
                "carteiras",
                filter=Q(carteiras__deleted=False),
                distinct=True,
            ),
            saldo_total_carteiras=Coalesce(
                Sum(
                    "carteiras__saldo",
                    filter=Q(carteiras__deleted=False),
                ),
                Value(Decimal("0")),
            ),
        )

    @admin.display(description="Carteiras ativas", ordering="carteiras_ativas_total")
    def carteiras_ativas(self, obj):
        return getattr(obj, "carteiras_ativas_total", 0)

    @admin.display(description="Saldo em carteiras", ordering="saldo_total_carteiras")
    def saldo_em_carteiras(self, obj):
        return obj.saldo_total_carteiras


@admin.register(ContaAssociado)
class ContaAssociadoAdmin(admin.ModelAdmin):
    list_display = ["user", "carteiras_ativas", "saldo_total_carteiras"]
    search_fields = ["user__email"]

    def get_queryset(self, request):  # type: ignore[override]
        queryset = super().get_queryset(request)
        return queryset.annotate(
            carteiras_ativas_total=Count(
                "carteiras",
                filter=Q(carteiras__deleted=False),
                distinct=True,
            ),
            saldo_carteiras_total=Coalesce(
                Sum(
                    "carteiras__saldo",
                    filter=Q(carteiras__deleted=False),
                ),
                Value(Decimal("0")),
            ),
        )

    @admin.display(description="Carteiras ativas", ordering="carteiras_ativas_total")
    def carteiras_ativas(self, obj):
        return getattr(obj, "carteiras_ativas_total", 0)

    @admin.display(description="Saldo em carteiras", ordering="saldo_carteiras_total")
    def saldo_total_carteiras(self, obj):
        saldo = getattr(obj, "saldo_carteiras_total", None)
        return saldo if saldo is not None else ZERO


@admin.register(Carteira)
class CarteiraAdmin(admin.ModelAdmin):
    list_display = ["nome", "vinculo", "tipo", "saldo_atual", "created_at"]
    list_filter = [
        "tipo",
        ("centro_custo", admin.RelatedOnlyFieldListFilter),
        ("conta_associado", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ["nome", "centro_custo__nome", "conta_associado__user__email"]
    list_select_related = ["centro_custo", "conta_associado"]

    @admin.display(description="Vínculo")
    def vinculo(self, obj):
        if obj.centro_custo_id:
            return obj.centro_custo
        if obj.conta_associado_id:
            return obj.conta_associado
        return "-"

    @admin.display(description="Saldo atual", ordering="saldo")
    def saldo_atual(self, obj):
        return obj.saldo


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


