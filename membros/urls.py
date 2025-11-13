from django.urls import path

from . import views

app_name = "membros"

urlpatterns = [
    path("", views.MembroListView.as_view(), name="membros_lista"),
    path(
        "api/section/",
        views.MembroSectionListView.as_view(),
        name="membros_lista_api",
    ),
    path("promover/", views.MembroPromoverListView.as_view(), name="membros_promover"),
    path(
        "promover/carousel/",
        views.MembroPromoverCarouselView.as_view(),
        name="membros_promover_carousel",
    ),
    path(
        "<int:pk>/promover/form/",
        views.MembroPromoverFormView.as_view(),
        name="membro_promover_form",
    ),
    path("novo/", views.OrganizacaoUserCreateView.as_view(), name="membros_adicionar"),
]
