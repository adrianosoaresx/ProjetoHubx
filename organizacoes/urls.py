from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("", views.OrganizacaoListView.as_view(), name="list"),
    path("nova/", views.OrganizacaoCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.OrganizacaoDetailView.as_view(), name="detail"),
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
