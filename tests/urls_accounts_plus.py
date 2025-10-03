from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("conexoes/", include(("conexoes.urls", "conexoes"), namespace="conexoes")),
    path("api/accounts/", include(("accounts.api_urls", "accounts_api"), namespace="accounts_api")),
    path(
        "api/conexoes/",
        include(("conexoes.api_urls", "conexoes_api"), namespace="conexoes_api"),
    ),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]
