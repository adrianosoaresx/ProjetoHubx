from django.urls import path

from . import views

app_name = "nucleos"

urlpatterns = [
    path("", views.NucleoListView.as_view(), name="list"),
    path("novo/", views.NucleoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.NucleoDetailView.as_view(), name="detail"),
    path("<int:pk>/metrics/", views.NucleoMetricsView.as_view(), name="metrics"),
    path("<int:pk>/editar/", views.NucleoUpdateView.as_view(), name="update"),
    path("<int:pk>/remover/", views.NucleoDeleteView.as_view(), name="delete"),
    path(
        "<int:pk>/solicitar/confirmar/",
        views.SolicitarParticipacaoModalView.as_view(),
        name="solicitar_modal",
    ),
    path("<int:pk>/participar/", views.ParticipacaoCreateView.as_view(), name="participacao_solicitar"),
    path(
        "<int:pk>/participacao/<int:participacao_id>/decidir/",
        views.ParticipacaoDecisaoView.as_view(),
        name="participacao_decidir",
    ),
    path(
        "<int:pk>/postar/novo/",
        views.PostarFeedModalView.as_view(),
        name="postar_modal",
    ),
    path(
        "<int:pk>/convites/",
        views.ConvitesModalView.as_view(),
        name="convites_modal",
    ),
    path(
        "<int:pk>/membro/<int:participacao_id>/remover/",
        views.MembroRemoveView.as_view(),
        name="membro_remover",
    ),
    path(
        "<int:pk>/membro/<int:participacao_id>/role/",
        views.MembroRoleView.as_view(),
        name="membro_role",
    ),
    path(
        "<int:pk>/suplentes/adicionar/",
        views.SuplenteCreateView.as_view(),
        name="suplente_adicionar",
    ),
    path(
        "<int:pk>/suplentes/<uuid:suplente_id>/remover/",
        views.SuplenteDeleteView.as_view(),
        name="suplente_remover",
    ),
    path(
        "<int:pk>/membros/exportar/",
        views.ExportarMembrosView.as_view(),
        name="exportar_membros",
    ),
    path(
        "<int:pk>/toggle-active/",
        views.NucleoToggleActiveView.as_view(),
        name="toggle_active",
    ),
]
