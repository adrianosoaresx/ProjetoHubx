from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.CategoriaListView.as_view(), name="index"),
    path("categorias/", views.CategoriaListView.as_view(), name="categorias"),
    path(
        "categorias/gerenciar/",
        views.CategoriaManageListView.as_view(),
        name="categoria_manage_list",
    ),
    path(
        "categorias/novo/",
        views.CategoriaCreateView.as_view(),
        name="categoria_create",
    ),
    path(
        "categorias/<int:pk>/editar/",
        views.CategoriaUpdateView.as_view(),
        name="categoria_update",
    ),
    path(
        "categorias/<int:pk>/remover/",
        views.CategoriaDeleteView.as_view(),
        name="categoria_delete",
    ),
    path(
        "categoria/<int:categoria_pk>/", views.TopicoListView.as_view(), name="topicos"
    ),
    path("topico/<int:pk>/", views.TopicoDetailView.as_view(), name="topico_detail"),
    path("topico/novo/", views.TopicoCreateView.as_view(), name="topico_create"),
    path(
        "topico/<int:topico_pk>/responder/",
        views.RespostaCreateView.as_view(),
        name="responder",
    ),
]
