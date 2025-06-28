from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<dest_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/chat/$", ChatConsumer.as_asgi()),
]
