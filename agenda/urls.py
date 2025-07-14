from django.urls import path

from . import views
from .views import (
    EventoCreateView,
    EventoDetailView,
    EventoUpdateView,
    EventoDeleteView,
    EventoSubscribeView,
    EventoRemoveInscritoView,
)

app_name = "agenda"

urlpatterns = [
    path("", views.calendario, name="calendario"),
    path("<int:ano>/<int:mes>/", views.calendario, name="calendario_mes"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    # CRUD
    path("evento/novo/", EventoCreateView.as_view(), name="evento_novo"),
    path("novo/", EventoCreateView.as_view(), name="evento_create"),
    path("<int:pk>/", EventoDetailView.as_view(), name="evento_detalhe"),
    path("<int:pk>/editar/", EventoUpdateView.as_view(), name="evento_editar"),
    path("<int:pk>/excluir/", EventoDeleteView.as_view(), name="evento_excluir"),
    path("<int:pk>/inscrever/", EventoSubscribeView.as_view(), name="evento_subscribe"),
    path(
        "<int:pk>/inscrito/<int:user_id>/remover/",
        EventoRemoveInscritoView.as_view(),
        name="evento_remover_inscrito",
    ),
]
