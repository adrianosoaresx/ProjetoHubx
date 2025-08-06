from __future__ import annotations

from django.urls import re_path

from .consumers import DiscussionConsumer

websocket_urlpatterns = [
    re_path(r"ws/discussao/(?P<topico_id>\d+)/", DiscussionConsumer.as_asgi()),
]
