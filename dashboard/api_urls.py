from rest_framework.routers import DefaultRouter

from .api import DashboardFilterViewSet, DashboardViewSet, DashboardCustomMetricViewSet

router = DefaultRouter()
router.register(r"dashboard/filters", DashboardFilterViewSet, basename="dashboard-filter")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")
router.register(
    r"dashboard/custom-metrics",
    DashboardCustomMetricViewSet,
    basename="dashboard-custom-metric",
)

urlpatterns = router.urls
