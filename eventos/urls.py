from django.urls import path
from . import views

app_name = "eventos"

urlpatterns = [
    path("", views.EventoCalendarView.as_view(), name="calendar"),
    path("lista/", views.EventoListView.as_view(), name="list"),
    path("novo/", views.EventoCreateView.as_view(), name="create"),
    path("<int:pk>/editar/", views.EventoUpdateView.as_view(), name="update"),
    path("<int:pk>/remover/", views.EventoDeleteView.as_view(), name="delete"),
    path(
        "<int:pk>/inscrito/<int:user_id>/remover/",
        views.EventoRemoveInscritoView.as_view(),
        name="remove_inscrito",
    ),
    path("<int:pk>/inscrever/", views.EventoSubscribeView.as_view(), name="subscribe"),
    path("<int:pk>/", views.EventoDetailView.as_view(), name="detail"),
]
