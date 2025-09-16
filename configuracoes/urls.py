from django.urls import path


from .views import ConfiguracoesView

app_name = "configuracoes"

urlpatterns = [
# Endpoint principal para a página de configurações.  Usa a classe
    # ConfiguracoesView para servir a página completa ou os fragmentos
    # correspondentes às abas quando a requisição é feita via HTMX.
    path("", ConfiguracoesView.as_view(), name="configuracoes"),
]
