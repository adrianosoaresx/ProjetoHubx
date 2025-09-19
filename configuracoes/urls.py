from django.urls import path


from .views import ConfiguracoesView

app_name = "configuracoes"

urlpatterns = [
    # Endpoint principal e rotas por seção (sem query string)
    path("", ConfiguracoesView.as_view(), name="configuracoes"),
    path("seguranca/", ConfiguracoesView.as_view(), {"section": "seguranca"}, name="configuracoes_seguranca"),
    path("preferencias/", ConfiguracoesView.as_view(), {"section": "preferencias"}, name="configuracoes_preferencias"),
]
