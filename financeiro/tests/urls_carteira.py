from django.urls import include, path

urlpatterns = [
    path("api/financeiro/", include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api")),
]
