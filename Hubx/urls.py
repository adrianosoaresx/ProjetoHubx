"""Hubx URL Configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # Página inicial (app core)
    path("", include(("core.urls", "core"), namespace="core")),
    # Dashboard web
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    # Apps de autenticação/usuário
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),
    # CRUD de Empresas, Organizações e Núcleos (front‑end)
    path("empresas/", include(("empresas.urls", "empresas"), namespace="empresas")),
    path("organizacoes/", include(("organizacoes.urls", "organizacoes"), namespace="organizacoes")),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    # Agenda/Eventos
    path("agenda/", include(("agenda.urls", "agenda"), namespace="agenda")),
    path("eventos/", RedirectView.as_view(url="/agenda/", permanent=True)),
    path("eventos/<path:rest>/", RedirectView.as_view(url="/agenda/%(rest)s", permanent=True)),
    # Chat, Discussão e Feed (web)
    path("chat/", include(("chat.urls", "chat"), namespace="chat")),
    path("discussao/", include(("discussao.urls", "discussao"), namespace="discussao")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
    path("financeiro/", include(("financeiro.urls", "financeiro"), namespace="financeiro")),
    path("select2/", include("django_select2.urls")),
    # APIs REST (subcaminhos específicos)
    path(
        "api/organizacoes/",
        include(("organizacoes.api_urls", "organizacoes_api"), namespace="organizacoes_api"),
    ),
    path(
        "api/nucleos/",
        include(("nucleos.api_urls", "nucleos_api"), namespace="nucleos_api"),
    ),
    path(
        "api/empresas/",
        include(("empresas.api_urls", "empresas_api"), namespace="empresas_api"),
    ),
    path(
        "api/dashboard/",
        include(("dashboard.api_urls", "dashboard_api"), namespace="dashboard_api"),
    ),
    path(
        "api/tokens/",
        include(("tokens.api_urls", "tokens_api"), namespace="tokens_api"),
    ),
    path(
        "api/configuracoes/",
        include(("configuracoes.api_urls", "configuracoes_api"), namespace="configuracoes_api"),
    ),
    path(
        "api/notificacoes/",
        include(("notificacoes.api_urls", "notificacoes_api"), namespace="notificacoes_api"),
    ),
    path(
        "api/accounts/",
        include(("accounts.api_urls", "accounts_api"), namespace="accounts_api"),
    ),
    path(
        "api/chat/",
        include(("chat.api_urls", "chat_api"), namespace="chat_api"),
    ),
    path(
        "api/discussao/",
        include(("discussao.api_urls", "discussao_api"), namespace="discussao_api"),
    ),
    path(
        "api/financeiro/",
        include(("financeiro.api_urls", "financeiro_api"), namespace="financeiro_api"),
    ),
    path(
        "api/feed/",
        include(("feed.api_urls", "feed_api"), namespace="feed_api"),
    ),
]

# Arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
