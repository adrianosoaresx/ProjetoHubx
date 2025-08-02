from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    NotificationLogViewSet,
    NotificationTemplateViewSet,
    UserNotificationPreferenceViewSet,
    enviar_view,
)

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="template")
router.register("logs", NotificationLogViewSet, basename="log")
router.register("preferencias", UserNotificationPreferenceViewSet, basename="preferencia")

urlpatterns = router.urls + [path("enviar/", enviar_view, name="enviar")]
