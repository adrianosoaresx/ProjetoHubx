from rest_framework.routers import DefaultRouter

from .api import EmpresaViewSet, TagViewSet

router = DefaultRouter()
router.register(r"empresas", EmpresaViewSet, basename="empresa")
router.register("empresas/tags", TagViewSet)

urlpatterns = router.urls
