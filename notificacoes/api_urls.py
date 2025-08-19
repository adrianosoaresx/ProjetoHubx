from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    NotificationLogViewSet,
    NotificationTemplateViewSet,
    UserNotificationPreferenceViewSet,
    PushSubscriptionViewSet,
    enviar_view,
)

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="template")
router.register("logs", NotificationLogViewSet, basename="log")
router.register("push/subscriptions", PushSubscriptionViewSet, basename="push-subscription")
router.register("preferences", UserNotificationPreferenceViewSet, basename="preference")
urlpatterns = router.urls + [
    path("enviar/", enviar_view, name="enviar"),
]
