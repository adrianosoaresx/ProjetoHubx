from django.urls import include, path

from configuracoes.views import ConfiguracoesView

urlpatterns = [
    path("configuracoes/", ConfiguracoesView.as_view(), name="configuracoes"),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("", include("Hubx.urls")),
]
