from django.urls import path

from . import views

app_name = "nucleos"

urlpatterns = [
    path("", views.NucleoListView.as_view(), name="list"),
    path("meus/", views.NucleoMeusView.as_view(), name="meus"),
    path("carousel/", views.NucleoListCarouselView.as_view(), name="nucleos_carousel_api"),
    path("novo/", views.NucleoCreateView.as_view(), name="create"),
    path("uuid/<uuid:public_id>/", views.NucleoDetailView.as_view(), name="detail_uuid"),
    path("<int:pk>/membros/", views.NucleoMembrosPartialView.as_view(), name="membros_list"),
    path("<int:pk>/nucleacao/", views.NucleacaoInviteView.as_view(), name="nucleacao_invite"),
    path(
        "solicitacoes/<int:participacao_id>/promover/",
        views.NucleacaoPromoverSolicitacaoView.as_view(),
        name="nucleacao_promover",
    ),
    path(
        "<int:pk>/membros/carousel/",
        views.NucleoMembrosCarouselView.as_view(),
        name="membros_carousel_api",
    ),
    path("<int:pk>/", views.NucleoDetailView.as_view(), name="detail"),
    path("<uuid:public_id>/editar/", views.NucleoUpdateView.as_view(), name="update"),
    path("<int:pk>/remover/", views.NucleoDeleteView.as_view(), name="delete"),
    path("<int:pk>/participar/", views.ParticipacaoCreateView.as_view(), name="participacao_solicitar"),
    path(
        "<int:pk>/participacao/<int:participacao_id>/decidir/",
        views.ParticipacaoDecisaoView.as_view(),
        name="participacao_decidir",
    ),
    path(
        "<int:pk>/membro/<int:participacao_id>/remover/",
        views.MembroRemoveView.as_view(),
        name="membro_remover",
    ),
    path(
        "<int:pk>/membro/<int:participacao_id>/promover/",
        views.MembroPromoverView.as_view(),
        name="membro_promover",
    ),
    path(
        "<int:pk>/suplentes/<uuid:suplente_id>/remover/",
        views.SuplenteDeleteView.as_view(),
        name="suplente_remover",
    ),
    path(
        "<int:pk>/toggle-active/",
        views.NucleoToggleActiveView.as_view(),
        name="toggle_active",
    ),
    path(
        "portfolio/<int:pk>/editar/",
        views.NucleoPortfolioUpdateView.as_view(),
        name="portfolio_edit",
    ),
    path(
        "portfolio/<int:pk>/remover/",
        views.NucleoPortfolioDeleteView.as_view(),
        name="portfolio_delete",
    ),
]
