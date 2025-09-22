from rest_framework.routers import DefaultRouter

from .api import (
    BriefingEventoViewSet,
    EventoViewSet,
    InscricaoEventoViewSet,
    ParceriaEventoViewSet,
    TarefaViewSet,
)

router = DefaultRouter()
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"inscricoes", InscricaoEventoViewSet, basename="inscricao")
router.register(r"parcerias", ParceriaEventoViewSet, basename="parceria")
router.register(r"briefings", BriefingEventoViewSet, basename="briefing")
router.register(r"tarefas", TarefaViewSet, basename="tarefa")

urlpatterns = router.urls
