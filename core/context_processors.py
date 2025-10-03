from django.conf import settings

from core.utils import get_back_navigation_fallback, resolve_back_href


def htmx_version(request):
    return {
        "HTMX_VERSION": getattr(settings, "HTMX_VERSION", ""),
        # Flag para habilitar/desabilitar inicialização de WebSocket no template
        "WEBSOCKETS_ENABLED": getattr(settings, "WEBSOCKETS_ENABLED", True),
    }


def menu_items(request):
    from .menu import build_menu

    return {"NAV_MENU": build_menu(request)}


def back_navigation(request):
    fallback = get_back_navigation_fallback(request)
    back_href = resolve_back_href(request, fallback=fallback)
    context = {"back_href": back_href}
    if fallback:
        context["back_component_config"] = {
            "href": back_href,
            "fallback_href": fallback,
        }
    return context
