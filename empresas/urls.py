from django.urls import path

from . import views

app_name = "empresas"

urlpatterns = [
    path("", views.EmpresaListView.as_view(), name="lista"),
    path("buscar/", views.buscar, name="buscar"),
    path("nova/", views.EmpresaCreateView.as_view(), name="empresa_criar"),
    path("<uuid:pk>/editar/", views.EmpresaUpdateView.as_view(), name="empresa_editar"),
    path("<uuid:pk>/", views.detalhes_empresa, name="detail"),
    path("tags/", views.TagListView.as_view(), name="tags_list"),
    path("tags/novo/", views.TagCreateView.as_view(), name="tags_create"),
    path("tags/<int:pk>/editar/", views.TagUpdateView.as_view(), name="tags_update"),
    path("tags/<int:pk>/remover/", views.TagDeleteView.as_view(), name="tags_delete"),
    path("<uuid:pk>/remover/", views.EmpresaDeleteView.as_view(), name="remover"),
    path("<uuid:empresa_id>/avaliar/", views.AvaliacaoCreateView.as_view(), name="avaliacao_criar"),
    path(
        "<uuid:empresa_id>/avaliar/editar/",
        views.AvaliacaoUpdateView.as_view(),
        name="avaliacao_editar",
    ),
    path("<int:empresa_id>/contatos/novo/", views.adicionar_contato, name="contato_novo"),
    path("contatos/<int:pk>/editar/", views.editar_contato, name="contato_editar"),
    path("contatos/<int:pk>/remover/", views.remover_contato, name="contato_remover"),
    path("<uuid:pk>/historico/", views.EmpresaChangeLogListView.as_view(), name="historico"),
    path("favoritas/", views.FavoritoListView.as_view(), name="favoritas"),
]
