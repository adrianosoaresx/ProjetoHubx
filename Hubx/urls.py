"""Hubx URL Configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.views import serve as static_serve
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog

from accounts import views

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # Página inicial (app core)
    path("", include(("core.urls", "core"), namespace="core")),
    # Apps de autenticação/usuário
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),
    # CRUD de Empresas, Organizações e Núcleos (front‑end)
    path("organizacoes/", include(("organizacoes.urls", "organizacoes"), namespace="organizacoes")),
    path("nucleos/", include(("nucleos.urls", "nucleos"), namespace="nucleos")),
    path("eventos/", include(("eventos.urls", "eventos"), namespace="eventos")),
    # Discussão e Feed (web)
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("notificacoes/", include(("notificacoes.urls", "notificacoes"), namespace="notificacoes")),
    path(
        "configuracoes/",
        include(("configuracoes.urls", "configuracoes"), namespace="configuracoes"),
    ),
    path("associados/", views.AssociadoListView.as_view(), name="associados_lista"),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
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
        "api/audit/",
        include(("audit.api_urls", "audit_api"), namespace="audit_api"),
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
        "api/feed/",
        include(("feed.api_urls", "feed_api"), namespace="feed_api"),
    ),
    path(
        "api/eventos/",
        include(("eventos.api_urls", "eventos_api"), namespace="eventos_api"),
    ),
    path("", include("django_prometheus.urls")),
]

# Arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
    urlpatterns += [
        path("service-worker.js", static_serve, kwargs={"path": "service-worker.js"}),
        path("manifest.json", static_serve, kwargs={"path": "manifest.json"}),
    ]
