from django.urls import path

from .views import ConfiguracoesView

app_name = "configuracoes"

urlpatterns = [
    path("", ConfiguracoesView.as_view(), name="configuracoes"),
]
