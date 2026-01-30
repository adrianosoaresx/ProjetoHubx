from django.urls import path

from . import views
from .views import (
    BriefingEventoFillView,
    BriefingEventoDetailView,
    BriefingTemplateCreateView,
    BriefingTemplateDeleteView,
    BriefingTemplateListView,
    BriefingTemplateSelectView,
    BriefingTemplateUpdateView,
    EventoCancelSubscriptionView,
    EventoCancelarInscricaoModalView,
    EventoCreateView,
    EventoDeleteView,
    EventoDetailView,
    EventoInscritosPDFView,
    EventoInscritosCarouselView,
    EventoInscritosPartialView,
    EventoFeedbackView,
    EventoRemoverInscritoModalView,
    EventoPortfolioDeleteView,
    EventoPortfolioUpdateView,
    EventoRemoveInscritoView,
    EventoSubscribeView,
    EventoUpdateView,
    InscricaoEventoCreateView,
    InscricaoEventoPagamentoCreateView,
    InscricaoEventoCheckoutView,
    InscricaoEventoOverviewView,
    InscricaoEventoUpdateView,
    InscricaoTogglePagamentoValidacaoView,
    InscricaoEventoListView,
    inscricao_resultado,
)

app_name = "eventos"

urlpatterns = [
    path("c/<str:short_code>/", views.convite_public_view, name="convite_public"),
    path("briefings/modelos/", BriefingTemplateListView.as_view(), name="briefing_template_list"),
    path(
        "briefings/modelos/novo/",
        BriefingTemplateCreateView.as_view(),
        name="briefing_template_create",
    ),
    path(
        "briefings/modelos/<int:pk>/editar/",
        BriefingTemplateUpdateView.as_view(),
        name="briefing_template_update",
    ),
    path(
        "briefings/modelos/<int:pk>/desativar/",
        BriefingTemplateDeleteView.as_view(),
        name="briefing_template_delete",
    ),
    path(
        "eventos/<uuid:evento_id>/briefing/selecionar/",
        BriefingTemplateSelectView.as_view(),
        name="briefing_selecionar",
    ),
    path(
        "eventos/<uuid:evento_id>/briefing/preencher/",
        BriefingEventoFillView.as_view(),
        name="briefing_preencher",
    ),
    path(
        "eventos/<uuid:evento_id>/briefing/visualizar/",
        BriefingEventoDetailView.as_view(),
        name="briefing_visualizar",
    ),
    path("lista/", views.EventoListView.as_view(), name="lista"),
    path(
        "lista/carousel/",
        views.EventoListCarouselView.as_view(),
        name="eventos_carousel_api",
    ),
    path("", views.painel_eventos, name="painel"),
    path("ultimos-30/", views.calendario_cards_ultimos_30, name="calendario"),
    path("<int:ano>/<int:mes>/", views.calendario, name="calendario_mes"),
    path("dia/<slug:dia_iso>/", views.lista_eventos, name="lista_eventos"),
    # CRUD
    path("evento/novo/", EventoCreateView.as_view(), name="evento_novo"),
    path("evento/<uuid:pk>/", EventoDetailView.as_view(), name="evento_detalhe"),
    path(
        "evento/<uuid:evento_id>/convites/novo/",
        views.convite_create,
        name="evento_convite_criar",
    ),
    path(
        "evento/<uuid:pk>/convites/carousel/",
        views.EventoConvitesCarouselView.as_view(),
        name="evento_convites_carousel",
    ),
    path("evento/<uuid:pk>/inscritos/", EventoInscritosPartialView.as_view(), name="evento_inscritos"),
    path(
        "evento/<uuid:pk>/inscritos/carousel/",
        EventoInscritosCarouselView.as_view(),
        name="evento_inscritos_carousel",
    ),
    path(
        "evento/<uuid:pk>/inscritos/pdf/",
        EventoInscritosPDFView.as_view(),
        name="evento_inscritos_pdf",
    ),
    path("evento/<uuid:pk>/editar/", EventoUpdateView.as_view(), name="evento_editar"),
    path("evento/<uuid:pk>/excluir/", EventoDeleteView.as_view(), name="evento_excluir"),
    path(
        "evento/<uuid:pk>/inscricao/overview/",
        InscricaoEventoOverviewView.as_view(),
        name="inscricao_overview",
    ),
    path(
        "evento/<uuid:pk>/inscricao/",
        InscricaoEventoCreateView.as_view(),
        name="inscricao_criar",
    ),
    path(
        "evento/<uuid:pk>/inscricao/checkout/",
        InscricaoEventoPagamentoCreateView.as_view(),
        name="inscricao_pagamentos_criar",
    ),
    path(
        "inscricoes/<uuid:uuid>/checkout/",
        InscricaoEventoCheckoutView.as_view(),
        name="inscricao_pagamento_checkout",
    ),
    path(
        "inscricoes/<uuid:uuid>/resultado/",
        inscricao_resultado,
        name="inscricao_resultado",
    ),
    path(
        "inscricoes/<uuid:uuid>/editar/",
        InscricaoEventoUpdateView.as_view(),
        name="inscricao_editar",
    ),
    path(
        "inscricoes/<uuid:uuid>/validacao/",
        InscricaoTogglePagamentoValidacaoView.as_view(),
        name="inscricao_toggle_validacao",
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
        "evento/<uuid:pk>/inscrito/<int:user_id>/remover/modal/",
        EventoRemoverInscritoModalView.as_view(),
        name="evento_remover_inscrito_modal",
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
        "evento/portfolio/<int:pk>/editar/",
        EventoPortfolioUpdateView.as_view(),
        name="evento_portfolio_edit",
    ),
    path(
        "evento/portfolio/<int:pk>/excluir/",
        EventoPortfolioDeleteView.as_view(),
        name="evento_portfolio_delete",
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
