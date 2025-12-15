from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from rest_framework.routers import DefaultRouter

from Hubx.urls import legacy_password_reset_redirect
from tokens.api import TokenViewSet

tokens_api_router = DefaultRouter()
tokens_api_router.register(r"tokens", TokenViewSet, basename="token")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("reset-password/", legacy_password_reset_redirect, name="password_reset_legacy"),
    path("", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("conexoes/", include(("conexoes.urls", "conexoes"), namespace="conexoes")),
    path("core/", include(("core.urls", "core"), namespace="core")),
    path(
        "api/notificacoes/",
        include(("notificacoes.api_urls", "notificacoes_api"), namespace="notificacoes_api"),
    ),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    path("organizacoes/", include(("organizacoes.urls", "organizacoes"), namespace="organizacoes")),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("portfolio/", include(("portfolio.urls", "portfolio"), namespace="portfolio")),
    path(
        "membros/",
        include(("membros.urls", "membros"), namespace="membros"),
    ),
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
        "api/audit/",
        include(("audit.api_urls", "audit_api"), namespace="audit_api"),
    ),
    path(
        "api/accounts/",
        include(("accounts.api_urls", "accounts_api"), namespace="accounts_api"),
    ),
    path(
        "api/conexoes/",
        include(("conexoes.api_urls", "conexoes_api"), namespace="conexoes_api"),
    ),
    path(
        "api/eventos/",
        include(("eventos.api_urls", "eventos_api"), namespace="eventos_api"),
    ),
    path(
        "api/feed/",
        include(("feed.api_urls", "feed_api"), namespace="feed_api"),
    ),
    path(
        "api/chat/",
        include(("ai_chat.api_urls", "ai_chat_api"), namespace="ai_chat_api"),
    ),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("select2/", include("django_select2.urls")),
]
