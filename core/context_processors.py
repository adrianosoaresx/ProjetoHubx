from django.conf import settings


def htmx_version(request):
    return {"HTMX_VERSION": getattr(settings, "HTMX_VERSION", "")}
