from django.urls import path

from .api import ConfiguracaoContaAPIView

urlpatterns = [
    path("configuracoes-conta/", ConfiguracaoContaAPIView.as_view(), name="configuracoes-conta"),
]
