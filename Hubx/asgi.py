# Hubx/asgi.py

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
django.setup()  # Deve vir antes de qualquer importação que acesse models

import chat.routing  # Agora é seguro importar  # noqa: E402
import discussao.routing  # noqa: E402
import notificacoes.routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
                + notificacoes.routing.websocket_urlpatterns
                + discussao.routing.websocket_urlpatterns
            )
        ),
    }
)
