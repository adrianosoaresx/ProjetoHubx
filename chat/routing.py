from django.urls import re_path

from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<channel_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
]
