from django.urls import include, path
from django.views.i18n import JavaScriptCatalog


urlpatterns = [
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),

from django.http import HttpResponse

urlpatterns = [
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path(
        "empresas/",
        include(([
            path("", lambda request: HttpResponse(""), name="lista"),
        ], "empresas")),
    ),

