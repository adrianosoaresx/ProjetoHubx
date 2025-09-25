from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from rest_framework.routers import DefaultRouter

from accounts import views as accounts_views
from tokens.api import TokenViewSet

tokens_api_router = DefaultRouter()
tokens_api_router.register(r"tokens", TokenViewSet, basename="token")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("core/", include(("core.urls", "core"), namespace="core")),
    path("api/notificacoes/", include("notificacoes.api_urls")),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
    path("financeiro/", include(("financeiro.urls", "financeiro"), namespace="financeiro")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    path("organizacoes/", include(("organizacoes.urls", "organizacoes"), namespace="organizacoes")),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),
    path("associados/", accounts_views.AssociadoListView.as_view(), name="associados_lista"),
    path(
        "configuracoes/",
        include(("configuracoes.urls", "configuracoes"), namespace="configuracoes"),
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
        "api/tokens/",
        include((tokens_api_router.urls, "tokens_api"), namespace="tokens_api"),
    ),
    path(
        "api/accounts/",
        include(("accounts.api_urls", "accounts_api"), namespace="accounts_api"),
    ),
    path(
        "api/eventos/",
        include(("eventos.api_urls", "eventos_api"), namespace="eventos_api"),
    ),
    path(
        "api/dashboard/",
        include(("dashboard.api_urls", "dashboard_api"), namespace="dashboard_api"),
    ),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("select2/", include("django_select2.urls")),
]
