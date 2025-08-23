from rest_framework.routers import DefaultRouter

from .api import TokenViewSet
from .api_views import ApiTokenIpViewSet, ApiTokenViewSet

app_name = "tokens_api"

router = DefaultRouter()
router.register(r"tokens", TokenViewSet, basename="token")
router.register(r"api-tokens", ApiTokenViewSet, basename="api-token")
router.register(r"api-token-ips", ApiTokenIpViewSet, basename="api-token-ip")

urlpatterns = router.urls
