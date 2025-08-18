from django.urls import include, path

from configuracoes.views import (
    ConfiguracoesView,
    ConfiguracaoContextualListView,
    ConfiguracaoContextualCreateView,
    ConfiguracaoContextualUpdateView,
    ConfiguracaoContextualDeleteView,
)

urlpatterns = [
    path("configuracoes/", ConfiguracoesView.as_view(), name="configuracoes"),
    path(
        "configuracoes/contextuais/",
        ConfiguracaoContextualListView.as_view(),
        name="configuracoes-contextual-list",
    ),
    path(
        "configuracoes/contextuais/nova/",
        ConfiguracaoContextualCreateView.as_view(),
        name="configuracoes-contextual-create",
    ),
    path(
        "configuracoes/contextuais/<uuid:pk>/editar/",
        ConfiguracaoContextualUpdateView.as_view(),
        name="configuracoes-contextual-update",
    ),
    path(
        "configuracoes/contextuais/<uuid:pk>/remover/",
        ConfiguracaoContextualDeleteView.as_view(),
        name="configuracoes-contextual-delete",
    ),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("", include("Hubx.urls")),
]
