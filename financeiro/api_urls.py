from __future__ import annotations

from rest_framework import routers

from .viewsets import (
    CentroCustoViewSet,
    FinanceiroViewSet,
    FinanceiroLogViewSet,
    FinanceiroTaskLogViewSet,
    ImportacaoPagamentosViewSet,
    LancamentoFinanceiroViewSet,
)

router = routers.DefaultRouter()
router.register("lancamentos", LancamentoFinanceiroViewSet, basename="lancamento")
router.register("centros", CentroCustoViewSet, basename="centro")
router.register("importacoes", ImportacaoPagamentosViewSet, basename="importacao")
router.register("logs", FinanceiroLogViewSet, basename="log")
router.register("task-logs", FinanceiroTaskLogViewSet, basename="task-log")
router.register("", FinanceiroViewSet, basename="financeiro")

urlpatterns = router.urls
