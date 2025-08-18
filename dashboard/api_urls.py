from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import DashboardFilterViewSet, DashboardViewSet, MetricDefinitionViewSet
from .api_views import FeedMetricsView

router = DefaultRouter()
router.register(r"dashboard/filters", DashboardFilterViewSet, basename="dashboard-filter")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")
router.register(
    r"dashboard/metric-definitions",
    MetricDefinitionViewSet,
    basename="metric-definition",
)

urlpatterns = router.urls + [
    path("feed/metrics/", FeedMetricsView.as_view(), name="feed-metrics"),
]
