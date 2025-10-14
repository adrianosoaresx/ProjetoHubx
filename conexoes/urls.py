from django.urls import path

from . import views

app_name = "conexoes"

urlpatterns = [
    path("perfil/sections/conexoes/", views.perfil_conexoes, name="perfil_sections_conexoes"),
    path(
        "perfil/conexoes/<int:id>/remover/modal/",
        views.remover_conexao_modal,
        name="remover_conexao_modal",
    ),
    path("perfil/conexoes/<int:id>/remover/", views.remover_conexao, name="remover_conexao"),
    path("perfil/conexoes/<int:id>/solicitar/", views.solicitar_conexao, name="solicitar_conexao"),
    path("perfil/conexoes/<int:id>/aceitar/", views.aceitar_conexao, name="aceitar_conexao"),
    path("perfil/conexoes/<int:id>/recusar/", views.recusar_conexao, name="recusar_conexao"),
    path("perfil/conexoes/buscar/", views.perfil_conexoes_buscar, name="perfil_conexoes_buscar"),
    path("perfil/partials/conexoes/", views.perfil_conexoes_partial, name="perfil_conexoes_partial"),
]
