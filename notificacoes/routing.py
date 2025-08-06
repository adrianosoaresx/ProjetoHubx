from django.urls import path

from .consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/notificacoes/", NotificationConsumer.as_asgi()),
]
