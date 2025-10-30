from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.list_portfolio, name="index"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/editar/", views.edit, name="edit"),
    path("<int:pk>/excluir/", views.delete, name="delete"),
]
