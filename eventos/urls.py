from django.urls import path

from . import views
from .views import (
    EventoCancelSubscriptionView,
    EventoCancelarInscricaoModalView,
    EventoCreateView,
    EventoDeleteView,
    EventoDetailView,
    EventoFeedbackView,
    EventoRemoveInscritoView,
    EventoSubscribeView,
    EventoUpdateView,
    InscricaoEventoCreateView,
    InscricaoEventoUpdateView,
    InscricaoEventoListView,
)

app_name = "eventos"

urlpatterns = [
    path("lista/", views.EventoListView.as_view(), name="lista"),
    path("", views.painel_eventos, name="painel"),
    path("ultimos-30/", views.calendario_cards_ultimos_30, name="calendario"),
    path("<int:ano>/<int:mes>/", views.calendario, name="calendario_mes"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    # CRUD
    path("evento/novo/", EventoCreateView.as_view(), name="evento_novo"),
    path("evento/<uuid:pk>/", EventoDetailView.as_view(), name="evento_detalhe"),
    path("evento/<uuid:pk>/editar/", EventoUpdateView.as_view(), name="evento_editar"),
    path("evento/<uuid:pk>/excluir/", EventoDeleteView.as_view(), name="evento_excluir"),
    path(
        "evento/<uuid:pk>/inscricao/",
        InscricaoEventoCreateView.as_view(),
        name="inscricao_criar",
    ),
    path(
        "inscricoes/<int:pk>/editar/",
        InscricaoEventoUpdateView.as_view(),
        name="inscricao_editar",
    ),
    path(
        "evento/<uuid:pk>/inscrever/",
        EventoSubscribeView.as_view(),
        name="evento_subscribe",
    ),
    path(
        "evento/<uuid:pk>/cancelar-inscricao/confirmar/",
        EventoCancelSubscriptionView.as_view(),
        name="evento_cancelar_inscricao",
    ),
    path(
        "evento/<uuid:pk>/cancelar-inscricao/",
        EventoCancelarInscricaoModalView.as_view(),
        name="evento_cancelar_inscricao_modal",
    ),
    path(
        "evento/<uuid:pk>/inscrito/<int:user_id>/remover/",
        EventoRemoveInscritoView.as_view(),
        name="evento_remover_inscrito",
    ),
    path(
        "evento/<uuid:pk>/feedback/",
        EventoFeedbackView.as_view(),
        name="evento_feedback",
    ),
    path("checkin/<int:pk>/", views.checkin_form, name="inscricao_checkin_form"),
    path(
        "api/inscricoes/<int:pk>/checkin/",
        views.checkin_inscricao,
        name="inscricao_checkin",
    ),
    path("api/eventos/<uuid:pk>/orcamento/", views.evento_orcamento, name="evento_orcamento"),
    path("eventos_por_dia/", views.eventos_por_dia, name="eventos_por_dia"),
    path("inscricoes/", InscricaoEventoListView.as_view(), name="inscricao_list"),
]
