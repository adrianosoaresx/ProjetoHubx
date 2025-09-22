from django.urls import path

from . import views
from .views import (
    BriefingEventoCreateView,
    BriefingEventoDetailView,
    BriefingEventoStatusView,
    EventoCreateView,
    EventoDeleteView,
    EventoDetailView,
    EventoFeedbackView,
    EventoRemoveInscritoView,
    EventoSubscribeView,
    EventoUpdateView,
    InscricaoEventoCreateView,
    InscricaoEventoListView,
    ParceriaEventoCreateView,
    ParceriaEventoDeleteView,
    ParceriaEventoListView,
    ParceriaEventoUpdateView,
    TarefaDetailView,
    TarefaCreateView,
    TarefaListView,
    TarefaUpdateView,
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
    path("checkin/<int:pk>/", views.checkin_form, name="inscricao_checkin_form"),
    path(
        "api/inscricoes/<int:pk>/checkin/",
        views.checkin_inscricao,
        name="inscricao_checkin",
    ),
    path("api/eventos/<uuid:pk>/orcamento/", views.evento_orcamento, name="evento_orcamento"),
    path("api/eventos/<uuid:pk>/espera/", views.fila_espera, name="fila_espera"),
    path("parceria/<int:pk>/avaliar/", views.avaliar_parceria, name="parceria_avaliar"),
    path("eventos_por_dia/", views.eventos_por_dia, name="eventos_por_dia"),
    path("inscricoes/", InscricaoEventoListView.as_view(), name="inscricao_list"),
    path("parcerias/", ParceriaEventoListView.as_view(), name="parceria_list"),
    path("parceria/novo/", ParceriaEventoCreateView.as_view(), name="parceria_criar"),
    path("parceria/<int:pk>/editar/", ParceriaEventoUpdateView.as_view(), name="parceria_editar"),
    path("parceria/<int:pk>/excluir/", ParceriaEventoDeleteView.as_view(), name="parceria_excluir"),
    path(
        "evento/<uuid:evento_pk>/briefing/",
        BriefingEventoDetailView.as_view(),
        name="briefing_detalhe",
    ),
    path(
        "briefing/novo/",
        BriefingEventoCreateView.as_view(),
        name="briefing_criar",
    ),
    path(
        "briefing/<int:pk>/status/<str:status>/",
        BriefingEventoStatusView.as_view(),
        name="briefing_status",
    ),
    path("tarefas/", TarefaListView.as_view(), name="tarefa_list"),
    path("tarefa/nova/", TarefaCreateView.as_view(), name="tarefa_criar"),
    path("tarefa/<uuid:pk>/editar/", TarefaUpdateView.as_view(), name="tarefa_editar"),
    path("tarefa/<uuid:pk>/", TarefaDetailView.as_view(), name="tarefa_detalhe"),
]
