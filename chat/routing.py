from django.urls import re_path

from .consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<channel_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/chat/notificacoes/$", NotificationConsumer.as_asgi()),
]
