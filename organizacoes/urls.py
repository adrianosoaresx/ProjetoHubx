from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("", views.OrganizacaoListView.as_view(), name="list"),
    path("nova/", views.OrganizacaoCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.OrganizacaoDetailView.as_view(), name="detail"),
    path(
        "<uuid:pk>/usuarios/modal/",
        views.OrganizacaoUsuariosModalView.as_view(),
        name="usuarios_modal",
    ),
    path(
        "<uuid:pk>/nucleos/modal/",
        views.OrganizacaoNucleosModalView.as_view(),
        name="nucleos_modal",
    ),
    path(
        "<uuid:pk>/eventos/modal/",
        views.OrganizacaoEventosModalView.as_view(),
        name="eventos_modal",
    ),
    path(
        "<uuid:pk>/empresas/modal/",
        views.OrganizacaoEmpresasModalView.as_view(),
        name="empresas_modal",
    ),
    path(
        "<uuid:pk>/posts/modal/",
        views.OrganizacaoPostsModalView.as_view(),
        name="posts_modal",
    ),
    path("<uuid:pk>/editar/", views.OrganizacaoUpdateView.as_view(), name="update"),
    path("<uuid:pk>/remover/", views.OrganizacaoDeleteView.as_view(), name="delete"),
    path(
        "<uuid:pk>/ativar/",
        views.OrganizacaoToggleActiveView.as_view(),
        name="toggle",
    ),
    path(
        "<uuid:pk>/historico/",
        views.OrganizacaoHistoryView.as_view(),
        name="historico",
    ),
]
