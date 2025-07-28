from __future__ import annotations

from rest_framework import routers

from .views import CentroCustoViewSet, FinanceiroViewSet

router = routers.DefaultRouter()
router.register("centros", CentroCustoViewSet, basename="centro")
router.register("", FinanceiroViewSet, basename="financeiro")

urlpatterns = router.urls
