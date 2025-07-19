from django.urls import path

from . import views

app_name = "empresas"

urlpatterns = [
    path("", views.lista_empresas, name="lista"),
    path("nova/", views.nova_empresa, name="nova"),
    path("<int:pk>/editar/", views.editar_empresa, name="editar"),
    path("<int:pk>/", views.detalhes_empresa, name="detail"),
    path("busca/", views.buscar_empresas, name="buscar"),
    path("tags/", views.TagListView.as_view(), name="tags_list"),
    path("tags/novo/", views.TagCreateView.as_view(), name="tags_create"),
    path("tags/<int:pk>/editar/", views.TagUpdateView.as_view(), name="tags_update"),
    path("tags/<int:pk>/remover/", views.TagDeleteView.as_view(), name="tags_delete"),
    path("criar/", views.criar_empresa, name="criar"),
    path("<int:pk>/deletar/", views.remover_empresa, name="deletar"),
    path("<int:pk>/remover/", views.remover_empresa, name="remover"),
    path("<int:empresa_id>/contatos/novo/", views.adicionar_contato, name="contato_novo"),
    path("contatos/<int:pk>/editar/", views.editar_contato, name="contato_editar"),
    path("contatos/<int:pk>/remover/", views.remover_contato, name="contato_remover"),
]
