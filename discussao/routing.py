from django.urls import path

from .consumers import DiscussionConsumer

websocket_urlpatterns = [
    path("ws/discussao/<int:topico_id>/", DiscussionConsumer.as_asgi()),
]
