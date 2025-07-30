from django.urls import path

from .views import (
    CategoriaListView,
    InteracaoView,
    RespostaCreateView,
    RespostaDeleteView,
    TopicoCreateView,
    TopicoDeleteView,
    TopicoDetailView,
    TopicoListView,
    TopicoUpdateView,
)

urlpatterns = [
    path("", CategoriaListView.as_view(), name="categorias"),
    path("<slug:categoria_slug>/", TopicoListView.as_view(), name="topicos"),
    path(
        "<slug:categoria_slug>/<slug:topico_slug>/",
        TopicoDetailView.as_view(),
        name="topico_detalhe",
    ),
    path("<slug:categoria_slug>/novo/", TopicoCreateView.as_view(), name="topico_criar"),
    path(
        "<slug:categoria_slug>/<slug:topico_slug>/editar/",
        TopicoUpdateView.as_view(),
        name="topico_editar",
    ),
    path(
        "<slug:categoria_slug>/<slug:topico_slug>/remover/",
        TopicoDeleteView.as_view(),
        name="topico_remover",
    ),
    path(
        "<slug:categoria_slug>/<slug:topico_slug>/responder/",
        RespostaCreateView.as_view(),
        name="resposta_criar",
    ),
    path(
        "comentario/<int:pk>/remover/",
        RespostaDeleteView.as_view(),
        name="delete_comment",
    ),
    path(
        "interacao/<int:content_type_id>/<int:object_id>/<str:tipo>/",
        InteracaoView.as_view(),
        name="interacao",
    ),
]
