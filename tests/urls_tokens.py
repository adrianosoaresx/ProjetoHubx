from django.urls import include, path

urlpatterns = [
    path("api/tokens/", include(("tokens.api_urls", "tokens_api"), namespace="tokens_api")),
]
