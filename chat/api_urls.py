from rest_framework_nested.routers import NestedDefaultRouter, DefaultRouter
from django.urls import path

from .api_views import ChatChannelViewSet, ChatMessageViewSet, exportar_conversa

router = DefaultRouter()
router.register(r"channels", ChatChannelViewSet, basename="chat-channel")

channels_router = NestedDefaultRouter(router, r"channels", lookup="channel")
channels_router.register(r"messages", ChatMessageViewSet, basename="chat-messages")

urlpatterns = router.urls + channels_router.urls + [
    path("channels/<uuid:channel_id>/exportar/", exportar_conversa, name="conversa_exportar"),
]

