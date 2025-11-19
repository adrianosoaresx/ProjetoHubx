from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .api import ChatMessageViewSet, ChatSessionViewSet

router = DefaultRouter()
router.register("sessions", ChatSessionViewSet, basename="chat-session")
router.register("messages", ChatMessageViewSet, basename="chat-message")

urlpatterns = router.urls
