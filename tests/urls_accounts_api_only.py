from django.urls import include, path

urlpatterns = [
    path("api/accounts/", include(("accounts.api_urls", "accounts_api"), namespace="accounts_api")),
    path(
        "api/conexoes/",
        include(("conexoes.api_urls", "conexoes_api"), namespace="conexoes_api"),
    ),
]
