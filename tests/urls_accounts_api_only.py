from django.urls import include, path

urlpatterns = [
    path("api/accounts/", include(("accounts.api_urls", "accounts_api"), namespace="accounts_api")),
]
