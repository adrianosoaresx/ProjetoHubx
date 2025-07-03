from django.urls import path
from . import views

app_name = "nucleos"

urlpatterns = [
    path("", views.NucleoListView.as_view(), name="list"),
    path("novo/", views.NucleoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.NucleoDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.NucleoUpdateView.as_view(), name="update"),
    path(
        "<int:pk>/membro/<int:user_id>/remover/",
        views.NucleoMemberRemoveView.as_view(),
        name="remove_member",
    ),
    path("<int:pk>/remover/", views.NucleoDeleteView.as_view(), name="delete"),
]
