from django.urls import path

from .api import ConfiguracaoContaViewSet, TestarNotificacaoView

configuracao_conta = ConfiguracaoContaViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    }
)

urlpatterns = [
    path("configuracoes-conta/", configuracao_conta, name="configuracoes-conta"),
    path("testar/", TestarNotificacaoView.as_view(), name="configuracoes-testar"),
]
