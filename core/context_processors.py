from django.conf import settings


def htmx_version(request):
    return {
        "HTMX_VERSION": getattr(settings, "HTMX_VERSION", ""),
        # Flag para habilitar/desabilitar inicialização de WebSocket no template
        "WEBSOCKETS_ENABLED": getattr(settings, "WEBSOCKETS_ENABLED", True),
    }
