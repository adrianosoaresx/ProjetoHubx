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

configuracao_contextual_list = ConfiguracaoContextualViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)
configuracao_contextual_detail = ConfiguracaoContextualViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path("configuracoes-conta/", configuracao_conta, name="configuracoes-conta"),
    path("contextuais/", configuracao_contextual_list, name="configuracoes-contextuais"),
    path(
        "contextuais/<uuid:pk>/",
        configuracao_contextual_detail,
        name="configuracoes-contextuais-detail",
    ),
    path("testar/", TestarNotificacaoView.as_view(), name="configuracoes-testar"),
]
