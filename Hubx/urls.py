"""Hubx URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # Página inicial (app core)
    path("", include(("core.urls", "core"), namespace="core")),

    path(
        "dashboard/",
        include(("dashboard.urls", "dashboard"), namespace="dashboard"),
    ),

    # Apps de autenticação/usuário
    path(
        "accounts/",
        include(("accounts.urls", "accounts"), namespace="accounts"),
    ),
    path("tokens/", include(("tokens.urls", "tokens"), namespace="tokens")),

    # CRUD de Empresas
    path(
        "empresas/",
        include(("empresas.urls", "empresas"), namespace="empresas"),
    ),
    path(
        "organizacoes/",
        include(("organizacoes.urls", "organizacoes"), namespace="organizacoes"),
    ),
    path(
        "nucleos/",
        include(("nucleos.urls", "nucleos"), namespace="nucleos"),
    ),
    path(
        "agenda/",
        include(("agenda.urls", "agenda"), namespace="agenda"),
    ),
    path(
        "eventos/",
        RedirectView.as_view(url="/agenda/", permanent=True),
    ),
    path(
        "eventos/<path:rest>/",
        RedirectView.as_view(url="/agenda/%(rest)s", permanent=True),
    ),
    path("chat/", include(("chat.urls", "chat"), namespace="chat")),
    path("forum/", include(("forum.urls", "forum"), namespace="forum")),
    path("feed/", include(("feed.urls", "feed"), namespace="feed")),
    path("select2/", include("django_select2.urls")),
]

# Arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
