from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import ChatMessageViewSet, exportar_conversa

router = DefaultRouter()
router.register(r"mensagens", ChatMessageViewSet, basename="mensagem")

urlpatterns = router.urls + [
    path("conversas/<uuid:channel_id>/exportar/", exportar_conversa, name="conversa_exportar"),
]
