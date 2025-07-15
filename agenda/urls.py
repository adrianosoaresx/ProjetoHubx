from django.urls import path

from . import views
from .views import (EventoCreateView, EventoDeleteView, EventoDetailView,
                    EventoFeedbackView, EventoRemoveInscritoView,
                    EventoSubscribeView, EventoUpdateView)

app_name = "agenda"

urlpatterns = [
    path("", views.calendario, name="calendario"),
    path("<int:ano>/<int:mes>/", views.calendario, name="calendario_mes"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    # CRUD
    path("evento/novo/", EventoCreateView.as_view(), name="evento_novo"),
    path("evento/<int:pk>/", EventoDetailView.as_view(), name="evento_detalhe"),
    path("evento/<int:pk>/editar/", EventoUpdateView.as_view(), name="evento_editar"),
    path("evento/<int:pk>/excluir/", EventoDeleteView.as_view(), name="evento_excluir"),
    path(
        "evento/<int:pk>/inscrever/",
        EventoSubscribeView.as_view(),
        name="evento_subscribe",
    ),
    path(
        "evento/<int:pk>/inscrito/<int:user_id>/remover/",
        EventoRemoveInscritoView.as_view(),
        name="evento_remover_inscrito",
    ),
    path(
        "evento/<int:pk>/feedback/",
        EventoFeedbackView.as_view(),
        name="evento_feedback",
    ),
    path("eventos_por_dia/", views.eventos_por_dia, name="eventos_por_dia"),
]
