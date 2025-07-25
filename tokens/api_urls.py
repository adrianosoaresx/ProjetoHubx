from rest_framework.routers import DefaultRouter

from .api import TokenViewSet

router = DefaultRouter()
router.register(r"tokens", TokenViewSet, basename="token")

urlpatterns = router.urls
