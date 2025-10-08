# Hubx/asgi.py

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from Hubx.env import load_env

load_env()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()  # Deve vir antes de qualquer importação que acesse models

import notificacoes.routing  # noqa: E402
import configuracoes.routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(notificacoes.routing.websocket_urlpatterns + configuracoes.routing.websocket_urlpatterns)
        ),
    }
)
