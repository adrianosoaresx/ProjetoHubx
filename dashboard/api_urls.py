from rest_framework.routers import DefaultRouter

from .api import DashboardFilterViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r"dashboard/filters", DashboardFilterViewSet, basename="dashboard-filter")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls
