from __future__ import annotations

from rest_framework import routers

app_name = "financeiro_api"

from .viewsets import (
    CarteiraViewSet,
    FinanceiroLogViewSet,
    FinanceiroTaskLogViewSet,
    ImportacaoPagamentosViewSet,
    LancamentoFinanceiroViewSet,
    RepasseViewSet,
)
from .views.api import FinanceiroViewSet

router = routers.DefaultRouter()
router.register("carteiras", CarteiraViewSet, basename="carteira")
router.register("lancamentos", LancamentoFinanceiroViewSet, basename="lancamento")
router.register("importacoes", ImportacaoPagamentosViewSet, basename="importacao")
router.register("logs", FinanceiroLogViewSet, basename="log")
router.register("task-logs", FinanceiroTaskLogViewSet, basename="task-log")
router.register("repasses", RepasseViewSet, basename="repasse")
router.register("", FinanceiroViewSet, basename="financeiro")

urlpatterns = router.urls
