from django.urls import include, path


urlpatterns = [
    path("", include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api")),
]
