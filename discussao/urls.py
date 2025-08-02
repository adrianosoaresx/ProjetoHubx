from django.urls import path

from .views import (
    CategoriaCreateView,
    CategoriaDeleteView,
    CategoriaListView,
    CategoriaUpdateView,
    InteracaoView,
    RespostaCreateView,
    RespostaDeleteView,
    RespostaUpdateView,
    TopicoCreateView,
    TopicoDeleteView,
    TopicoDetailView,
    TopicoListView,
    TopicoMarkResolvedView,
    TopicoUpdateView,
)

urlpatterns = [
    path("", CategoriaListView.as_view(), name="categorias"),
    path("categorias/novo/", CategoriaCreateView.as_view(), name="categoria_criar"),
    path("categorias/<slug:slug>/editar/", CategoriaUpdateView.as_view(), name="categoria_editar"),
    path("categorias/<slug:slug>/remover/", CategoriaDeleteView.as_view(), name="categoria_remover"),
    path(
        "comentario/<int:pk>/editar/",
        RespostaUpdateView.as_view(),
        name="resposta_editar",
    ),
    path(
        "comentario/<int:pk>/remover/",
        RespostaDeleteView.as_view(),
        name="delete_comment",
    ),
    path("<slug:categoria_slug>/", TopicoListView.as_view(), name="topicos"),
    path("<slug:categoria_slug>/novo/", TopicoCreateView.as_view(), name="topico_criar"),
    path(
        "<slug:categoria_slug>/<slug:topico_slug>/",
        TopicoDetailView.as_view(),
        name="topico_detalhe",
    ),
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
        "<slug:categoria_slug>/<slug:topico_slug>/resolver/",
        TopicoMarkResolvedView.as_view(),
        name="topico_resolver",
    ),
    path(
        "interacao/<int:content_type_id>/<int:object_id>/<str:acao>/",
        InteracaoView.as_view(),
        name="interacao",
    ),
]
