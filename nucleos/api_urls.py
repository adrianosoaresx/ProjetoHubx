from rest_framework.routers import DefaultRouter

from .api import NucleoViewSet

router = DefaultRouter()
router.register(r"nucleos", NucleoViewSet, basename="nucleo")

urlpatterns = router.urls
