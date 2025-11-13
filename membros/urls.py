from django.urls import path

from . import views

app_name = "membros"

urlpatterns = [
    path("", views.AssociadoListView.as_view(), name="membros_lista"),
    path(
        "api/section/",
        views.AssociadoSectionListView.as_view(),
        name="membros_lista_api",
    ),
    path("promover/", views.AssociadoPromoverListView.as_view(), name="membros_promover"),
    path(
        "promover/carousel/",
        views.AssociadoPromoverCarouselView.as_view(),
        name="membros_promover_carousel",
    ),
    path(
        "<int:pk>/promover/form/",
        views.AssociadoPromoverFormView.as_view(),
        name="membro_promover_form",
    ),
    path("novo/", views.OrganizacaoUserCreateView.as_view(), name="membros_adicionar"),
]
