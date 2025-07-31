from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("", views.OrganizacaoListView.as_view(), name="list"),
    path("nova/", views.OrganizacaoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OrganizacaoDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.OrganizacaoUpdateView.as_view(), name="update"),
    path("<int:pk>/remover/", views.OrganizacaoDeleteView.as_view(), name="delete"),
    path(
        "<int:pk>/ativar/",
        views.OrganizacaoToggleActiveView.as_view(),
        name="toggle",
    ),
    path(
        "<int:pk>/logs/",
        views.OrganizacaoLogListView.as_view(),
        name="logs",
    ),
]
