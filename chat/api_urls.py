from django.urls import path
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter

from .api_views import ChatChannelViewSet, ChatMessageViewSet, ModeracaoViewSet

router = DefaultRouter()
router.register(r"channels", ChatChannelViewSet, basename="chat-channel")
router.register(r"moderacao/messages", ModeracaoViewSet, basename="chat-moderacao")

channels_router = NestedDefaultRouter(router, r"channels", lookup="channel")
channels_router.register(r"messages", ChatMessageViewSet, basename="chat-messages")

urlpatterns = router.urls + channels_router.urls + [
    path(
        "moderacao/flags/",
        ModeracaoViewSet.as_view({"get": "list"}),
        name="chat-flags",
    ),
]

