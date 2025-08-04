from rest_framework.routers import DefaultRouter

from .api import (
    BriefingEventoViewSet,
    EventoViewSet,
    InscricaoEventoViewSet,
    MaterialDivulgacaoEventoViewSet,
    ParceriaEventoViewSet,
)

router = DefaultRouter()
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"inscricoes", InscricaoEventoViewSet, basename="inscricao")
router.register(r"materiais", MaterialDivulgacaoEventoViewSet, basename="material")
router.register(r"parcerias", ParceriaEventoViewSet, basename="parceria")
router.register(r"briefings", BriefingEventoViewSet, basename="briefing")

urlpatterns = router.urls
