from rest_framework.routers import DefaultRouter

from .api import OrganizacaoViewSet

router = DefaultRouter()
router.register(r"organizacoes", OrganizacaoViewSet, basename="organizacao")

urlpatterns = router.urls
