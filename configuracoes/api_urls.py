from django.urls import path

from .api import (
    ConfiguracaoContaViewSet,
    ConfiguracaoContextualViewSet,
    TestarNotificacaoView,
)

configuracao_conta = ConfiguracaoContaViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    }
)

contextuais = ConfiguracaoContextualViewSet.as_view({
    "get": "list",
    "post": "create",
})
contextuais_detail = ConfiguracaoContextualViewSet.as_view({
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("configuracoes-conta/", configuracao_conta, name="configuracoes-conta"),
    path("contextuais/", contextuais, name="configuracoes-contextuais"),
    path("contextuais/<int:pk>/", contextuais_detail, name="configuracoes-contextuais-detail"),
    path("testar/", TestarNotificacaoView.as_view(), name="configuracoes-testar"),
]
