from rest_framework.routers import DefaultRouter

from .api import EventoViewSet, InscricaoEventoViewSet, ParceriaEventoViewSet

router = DefaultRouter()
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"inscricoes", InscricaoEventoViewSet, basename="inscricao")
router.register(r"parcerias", ParceriaEventoViewSet, basename="parceria")
urlpatterns = router.urls
