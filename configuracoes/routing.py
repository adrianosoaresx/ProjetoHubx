from django.urls import path

from .consumers import ConfiguracoesConsumer

websocket_urlpatterns = [
    path("ws/configuracoes/", ConfiguracoesConsumer.as_asgi()),
]
