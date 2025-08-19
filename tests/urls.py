from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path("api/notificacoes/", include("notificacoes.api_urls")),
    path("financeiro/", include(("financeiro.urls", "financeiro"), namespace="financeiro")),

    path(
        "api/financeiro/",
        include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api"),
    ),

    path(
        "api/nucleos/",
        include(("nucleos.api_urls", "nucleos_api"), namespace="nucleos_api"),
    ),

    path(
        "api/organizacoes/",
        include(("organizacoes.api_urls", "organizacoes_api"), namespace="organizacoes_api"),
    ),

    path(
        "api/empresas/",
        include(("empresas.api_urls", "empresas_api"), namespace="empresas_api"),
    ),

    path(
        "api/tokens/",
        include(("tokens.api_urls", "tokens_api"), namespace="tokens_api"),
    ),


    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),

]
