from django.urls import path

from . import views

app_name = "nucleos"

urlpatterns = [
    path("", views.NucleoListView.as_view(), name="list"),
    path("meus/", views.NucleoMeusView.as_view(), name="meus"),
    path("carousel/", views.NucleoListCarouselView.as_view(), name="nucleos_carousel_api"),
    path("novo/", views.NucleoCreateView.as_view(), name="create"),
    path("uuid/<uuid:public_id>/", views.NucleoUuidRedirectView.as_view(), name="detail_uuid"),
    path("<uuid:public_id>/membros/", views.NucleoMembrosPartialView.as_view(), name="membros_list"),
    path("<int:pk>/membros/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:membros_list"), name="membros_list_legacy"),
    path("<uuid:public_id>/nucleacao/", views.NucleacaoInviteView.as_view(), name="nucleacao_invite"),
    path("<uuid:public_id>/card-cta/", views.NucleoCardCtaPartialView.as_view(), name="nucleo_card_cta"),
    path("<int:pk>/nucleacao/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:nucleacao_invite"), name="nucleacao_invite_legacy"),
    path(
        "solicitacoes/<int:participacao_id>/promover/",
        views.NucleacaoPromoverSolicitacaoView.as_view(),
        name="nucleacao_promover",
    ),
    path(
        "solicitacoes/<int:participacao_id>/cancelar/",
        views.NucleacaoCancelarSolicitacaoView.as_view(),
        name="nucleacao_cancelar",
    ),
    path(
        "<uuid:public_id>/membros/carousel/",
        views.NucleoMembrosCarouselView.as_view(),
        name="membros_carousel_api",
    ),
    path("<int:pk>/membros/carousel/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:membros_carousel_api"), name="membros_carousel_api_legacy"),
    path("<uuid:public_id>/", views.NucleoDetailView.as_view(), name="detail"),
    path("<int:pk>/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:detail"), name="detail_legacy"),
    path("<uuid:public_id>/editar/", views.NucleoUpdateView.as_view(), name="update"),
    path("<uuid:public_id>/remover/", views.NucleoDeleteView.as_view(), name="delete"),
    path("<int:pk>/remover/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:delete"), name="delete_legacy"),
    path("<uuid:public_id>/participar/", views.ParticipacaoCreateView.as_view(), name="participacao_solicitar"),
    path("<int:pk>/participar/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:participacao_solicitar"), name="participacao_solicitar_legacy"),
    path(
        "<uuid:public_id>/participacao/<int:participacao_id>/decidir/",
        views.ParticipacaoDecisaoView.as_view(),
        name="participacao_decidir",
    ),
    path("<int:pk>/participacao/<int:participacao_id>/decidir/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:participacao_decidir"), name="participacao_decidir_legacy"),
    path(
        "<uuid:public_id>/membro/<int:participacao_id>/remover/",
        views.MembroRemoveView.as_view(),
        name="membro_remover",
    ),
    path("<int:pk>/membro/<int:participacao_id>/remover/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:membro_remover"), name="membro_remover_legacy"),
    path(
        "<uuid:public_id>/membro/<int:participacao_id>/promover/",
        views.MembroPromoverView.as_view(),
        name="membro_promover",
    ),
    path("<int:pk>/membro/<int:participacao_id>/promover/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:membro_promover"), name="membro_promover_legacy"),
    path(
        "<uuid:public_id>/suplentes/<uuid:suplente_id>/remover/",
        views.SuplenteDeleteView.as_view(),
        name="suplente_remover",
    ),
    path("<int:pk>/suplentes/<uuid:suplente_id>/remover/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:suplente_remover"), name="suplente_remover_legacy"),
    path(
        "<uuid:public_id>/toggle-active/",
        views.NucleoToggleActiveView.as_view(),
        name="toggle_active",
    ),
    path("<int:pk>/toggle-active/", views.NucleoLegacyRedirectView.as_view(target_name="nucleos:toggle_active"), name="toggle_active_legacy"),
    path(
        "<uuid:public_id>/portfolio/<int:pk>/editar/",
        views.NucleoPortfolioUpdateView.as_view(),
        name="portfolio_edit",
    ),
    path("portfolio/<int:pk>/editar/", views.NucleoPortfolioLegacyRedirectView.as_view(target_name="nucleos:portfolio_edit"), name="portfolio_edit_legacy"),
    path(
        "<uuid:public_id>/portfolio/<int:pk>/remover/",
        views.NucleoPortfolioDeleteView.as_view(),
        name="portfolio_delete",
    ),
    path("portfolio/<int:pk>/remover/", views.NucleoPortfolioLegacyRedirectView.as_view(target_name="nucleos:portfolio_delete"), name="portfolio_delete_legacy"),
]
