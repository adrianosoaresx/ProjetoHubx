from django.http import HttpResponse
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog


def _core_home(_request):
    return HttpResponse("ok")


core_patterns = [
    path("", _core_home, name="home"),
    path("about/", _core_home, name="about"),
]

urlpatterns = [
    path("", include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api")),
    path("core/", include((core_patterns, "core"), namespace="core")),
    path("about/", _core_home, name="about"),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]
