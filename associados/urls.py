from django.urls import path

from . import views

app_name = "associados"

urlpatterns = [
    path("", views.AssociadoListView.as_view(), name="associados_lista"),
    path(
        "api/section/",
        views.AssociadoSectionListView.as_view(),
        name="associados_lista_api",
    ),
    path("promover/", views.AssociadoPromoverListView.as_view(), name="associados_promover"),
    path(
        "<int:pk>/promover/form/",
        views.AssociadoPromoverFormView.as_view(),
        name="associado_promover_form",
    ),
    path("novo/", views.OrganizacaoUserCreateView.as_view(), name="associados_adicionar"),
]
