from django.urls import path

from . import views
from .views import (
    BriefingEventoCreateView,
    BriefingEventoListView,
    BriefingEventoStatusView,
    BriefingEventoUpdateView,
    EventoCreateView,
    EventoDeleteView,
    EventoDetailView,
    EventoFeedbackView,
    EventoRemoveInscritoView,
    EventoSubscribeView,
    EventoUpdateView,
    InscricaoEventoListView,
    MaterialDivulgacaoEventoListView,
    ParceriaEventoCreateView,
    ParceriaEventoDeleteView,
    ParceriaEventoListView,
    ParceriaEventoUpdateView,
)

app_name = "agenda"

urlpatterns = [
    path("", views.calendario, name="calendario"),
    path("<int:ano>/<int:mes>/", views.calendario, name="calendario_mes"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    # CRUD
    path("evento/novo/", EventoCreateView.as_view(), name="evento_novo"),
    path("evento/<uuid:pk>/", EventoDetailView.as_view(), name="evento_detalhe"),
    path("evento/<uuid:pk>/editar/", EventoUpdateView.as_view(), name="evento_editar"),
    path("evento/<uuid:pk>/excluir/", EventoDeleteView.as_view(), name="evento_excluir"),
    path(
        "evento/<uuid:pk>/inscrever/",
        EventoSubscribeView.as_view(),
        name="evento_subscribe",
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
    path(
        "api/inscricoes/<int:pk>/checkin/",
        views.checkin_inscricao,
        name="inscricao_checkin",
    ),
    path("api/eventos/<uuid:pk>/orcamento/", views.evento_orcamento, name="evento_orcamento"),
    path("api/eventos/<uuid:pk>/espera/", views.fila_espera, name="fila_espera"),
    path("api/parcerias/<int:pk>/avaliar/", views.avaliar_parceria, name="parceria_avaliar"),
    path("eventos_por_dia/", views.eventos_por_dia, name="eventos_por_dia"),
    path("inscricoes/", InscricaoEventoListView.as_view(), name="inscricao_list"),
    path("materiais/", MaterialDivulgacaoEventoListView.as_view(), name="material_list"),
    path("parcerias/", ParceriaEventoListView.as_view(), name="parceria_list"),
    path("parceria/novo/", ParceriaEventoCreateView.as_view(), name="parceria_criar"),
    path("parceria/<int:pk>/editar/", ParceriaEventoUpdateView.as_view(), name="parceria_editar"),
    path("parceria/<int:pk>/excluir/", ParceriaEventoDeleteView.as_view(), name="parceria_excluir"),
    path("briefings/", BriefingEventoListView.as_view(), name="briefing_list"),
    path(
        "briefing/novo/",
        BriefingEventoCreateView.as_view(),
        name="briefing_criar",
    ),
    path(
        "briefing/<int:pk>/editar/",
        BriefingEventoUpdateView.as_view(),
        name="briefing_editar",
    ),
    path(
        "briefing/<int:pk>/status/<str:status>/",
        BriefingEventoStatusView.as_view(),
        name="briefing_status",
    ),
]
