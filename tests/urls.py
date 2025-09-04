from django.urls import include, path
from django.contrib import admin
from django.views.i18n import JavaScriptCatalog

from configuracoes.views import ConfiguracoesView
from accounts import views as accounts_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("core/", include(("core.urls", "core"), namespace="core")),
    path("api/notificacoes/", include("notificacoes.api_urls")),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
    path("financeiro/", include(("financeiro.urls", "financeiro"), namespace="financeiro")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("empresas/", include(("empresas.urls", "empresas"), namespace="empresas")),
    path("agenda/", include(("eventos.urls", "agenda"), namespace="agenda")),
    path("discussao/", include(("discussao.urls", "discussao"), namespace="discussao")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    path("organizacoes/", include(("organizacoes.urls", "organizacoes"), namespace="organizacoes")),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),

    path("associados/", accounts_views.AssociadoListView.as_view(), name="associados_lista"),

    path("configuracoes/", ConfiguracoesView.as_view(), name="configuracoes"),
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
    path(
        "api/accounts/",
        include(("accounts.api_urls", "accounts_api"), namespace="accounts_api"),
    ),
    path(
        "api/agenda/",
        include(("eventos.api_urls", "agenda_api"), namespace="agenda_api"),
    ),
    path(
        "api/dashboard/",
        include(("dashboard.api_urls", "dashboard_api"), namespace="dashboard_api"),
    ),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("select2/", include("django_select2.urls")),
]
