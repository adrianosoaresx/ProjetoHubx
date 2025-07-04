
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
]
