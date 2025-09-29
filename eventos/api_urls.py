from rest_framework.routers import DefaultRouter

from .api import EventoViewSet, InscricaoEventoViewSet

router = DefaultRouter()
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"inscricoes", InscricaoEventoViewSet, basename="inscricao")
urlpatterns = router.urls
