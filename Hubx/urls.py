"""Hubx URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # Página inicial (app core)
    path("", include("core.urls")),

    # Apps de autenticação/usuário
    path(
        "accounts/",
        include(("accounts.urls", "accounts"), namespace="accounts"),
    ),

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
        "eventos/",
        include(("eventos.urls", "eventos"), namespace="eventos"),
    ),
    path("select2/", include("django_select2.urls")),
]

# Arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
