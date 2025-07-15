from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("", views.OrganizacaoListView.as_view(), name="list"),
    path("nova/", views.OrganizacaoCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.OrganizacaoUpdateView.as_view(), name="update"),
    path("<int:pk>/remover/", views.OrganizacaoDeleteView.as_view(), name="delete"),
]
