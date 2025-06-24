from django.urls import path
from . import views

app_name = "forum"

urlpatterns = [
    path("", views.CategoriaListView.as_view(), name="categorias"),
    path("categoria/<int:categoria_pk>/", views.TopicoListView.as_view(), name="topicos"),
    path("topico/<int:pk>/", views.TopicoDetailView.as_view(), name="topico_detail"),
    path("topico/novo/", views.TopicoCreateView.as_view(), name="topico_create"),
    path("topico/<int:topico_pk>/responder/", views.RespostaCreateView.as_view(), name="responder"),
]
