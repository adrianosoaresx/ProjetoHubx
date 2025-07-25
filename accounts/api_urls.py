from rest_framework.routers import DefaultRouter

from .api import AccountViewSet

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")

urlpatterns = router.urls
