from django.urls import include, path

urlpatterns = [
    path("api/notificacoes/", include("notificacoes.api_urls")),
    path("financeiro/", include(("financeiro.urls", "financeiro"), namespace="financeiro")),

]
